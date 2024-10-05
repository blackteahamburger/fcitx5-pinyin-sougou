import argparse
import concurrent.futures
import logging
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter


class SougouSpider:
	def __init__(
		self,
		save_path=Path("sougou_dict"),
		skip_categories=[],
		concurrent_downloads=os.cpu_count() * 2,
		max_retries=5,
		timeout=60.0,
		keep_going=False,
		headers={
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:60.0) Gecko/20100101 Firefox/60.0",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
			"Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
			"Accept-Encoding": "gzip, deflate",
			"Connection": "keep-alive",
		},
	):
		self.save_path = save_path
		self.skip_categories = skip_categories
		self.max_retries = max_retries
		self.timeout = timeout
		self.keep_going = keep_going
		self.headers = headers
		self.logger = logging.getLogger(__name__)
		self.logger.addHandler(logging.NullHandler())
		self.__concurrent_downloads = concurrent_downloads
		self.__executor = concurrent.futures.ThreadPoolExecutor(concurrent_downloads)

	def __enter__(self):
		self.__executor.__enter__()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		return self.__executor.__exit__(exc_type, exc_val, exc_tb)

	@property
	def concurrent_downloads(self):
		return self.__concurrent_downloads

	def __create_category_dir(self, category, category_path):
		if category_path.is_dir() and category in self.skip_categories:
			self.logger.info(f"{category_path} already exists, skipping...")
			return False
		category_path.mkdir(exist_ok=True)
		return True

	def __recursive_as_completed(self, fs):
		if not fs:
			return
		for future in concurrent.futures.as_completed(fs):
			try:
				self.__recursive_as_completed(future.result())
			except Exception as e:
				self.logger.error(e)
				if not self.keep_going:
					sys.exit(1)

	def __get_html(self, url):
		with requests.Session() as session:
			session.mount("https://", HTTPAdapter(max_retries=self.max_retries))
			return session.get(url, headers=self.headers, timeout=self.timeout)

	def __download(self, name, url, category_path):
		file_path = category_path / (name + ".scel")
		if file_path.is_file():
			self.logger.warning(f"{file_path} already exists, skipping...")
			return
		retries = 0
		while not (content := self.__get_html(url).content):
			if retries == 5:
				# For dictionaries like 威海地名
				self.logger.warning(f"{file_path.name} is empty, skipping...")
				return
			retries += 1
		file_path.write_bytes(content)
		self.logger.info(f"{file_path.name} download succeeded.")

	def __download_page(self, page_url, category_path):
		return [
			self.__executor.submit(
				self.__download,
				(
					# For dictionaries like 天线行业/BSA
					dict_td_title.string.replace("/", "-")
					.replace(",", "-")
					.replace("|", "-")
					.replace("\\", "-")
					.replace("'", "-")
					if (
						dict_td_title := dict_td.find("div", class_="detail_title").a
					).string
					else ""  # For dictionaries without a name like index 15946
				)
				+ "_"
				+ dict_td_title["href"].rpartition("/")[-1],
				dict_td.find("div", class_="dict_dl_btn").a["href"],
				category_path,
			)
			for dict_td in BeautifulSoup(
				self.__get_html(page_url).text, "html.parser"
			).find_all("div", class_="dict_detail_block")
		]

	def __download_category(self, category, save_path=None):
		category_url = "https://pinyin.sogou.com/dict/cate/index/" + category
		soup = BeautifulSoup(self.__get_html(category_url).text, "html.parser")
		if save_path is None:
			save_path = self.save_path
		category_path = save_path / (
			soup.find("title").string.partition("_")[0] + "_" + category
		)
		if not self.__create_category_dir(category, category_path):
			return
		pages = soup.find("div", id="dict_page_list").find_all("a")
		return [
			self.__executor.submit(
				self.__download_page,
				category_url + "/default/" + str(page),
				category_path,
			)
			for page in range(1, 2 if len(pages) < 2 else int(pages[-2].string) + 1)
		]

	def __download_category_167(self):
		"""For category 167 that does not have a page"""
		category_path = self.save_path / "城市信息大全_167"
		if not self.__create_category_dir("167", category_path):
			return
		return [
			self.__executor.submit(
				self.__download_category,
				category_td.a["href"].rpartition("/")[-1],
				category_path,
			)
			for category_td in BeautifulSoup(
				self.__get_html("https://pinyin.sogou.com/dict/cate/index/180").text,
				"html.parser",
			).find_all("div", class_="citylistcate")
		]

	def __download_category_0(self):
		"""For dictionaries that do not belong to any categories"""
		category_path = self.save_path / "未分类_0"
		if not self.__create_category_dir("0", category_path):
			return
		return [
			self.__executor.submit(
				self.__download,
				"网络流行新词【官方推荐】_4",
				"https://pinyin.sogou.com/d/dict/download_cell.php?id=4&name=网络流行新词【官方推荐】",
				category_path,
			),
			*(
				self.__executor.submit(
					self.__download,
					(
						dict_td_title := dict_td.find("div", class_="rcmd_dict_title").a
					).string
					+ "_"
					+ dict_td_title["href"].rpartition("/")[-1],
					"https:" + dict_td.find("div", class_="rcmd_dict_dl_btn").a["href"],
					category_path,
				)
				for dict_td in BeautifulSoup(
					self.__get_html(
						"https://pinyin.sogou.com/dict/detail/index/4"
					).text,
					"html.parser",
				).find_all("div", class_="rcmd_dict")
			),
		]

	def download_dicts(self, categories=None):
		try:
			self.save_path.mkdir(parents=True, exist_ok=True)
			categories = (
				[
					"0",
					*(
						category.a["href"].partition("?")[0].rpartition("/")[-1]
						for category in BeautifulSoup(
							self.__get_html("https://pinyin.sogou.com/dict/").text,
							"html.parser",
						).find_all("div", class_="dict_category_list_title")
					),
				]
				if categories is None
				else list(set(categories))
			)
		except Exception as e:
			self.logger.error(e)
			sys.exit(1)
		self.__recursive_as_completed([
			self.__executor.submit(self.__download_category_0)
			if category == "0"
			else self.__executor.submit(self.__download_category_167)
			if category == "167"
			else self.__executor.submit(self.__download_category, category)
			for category in categories
		])


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="A Sougou dictionary spider.",
		formatter_class=argparse.RawTextHelpFormatter,
	)
	parser.add_argument(
		"--directory",
		"-d",
		default="sougou_dict",
		type=Path,
		help="The directory to save dictionaries.\n" "Default: sougou_dict.",
		metavar="DIR",
	)
	parser.add_argument(
		"--categories",
		"-c",
		nargs="+",
		help="List of category indexes to be downloaded.\n"
		"Categories are not separated to their subcategories except category 167 since it does not have a webpage.\n"
		"Special category 0 is for dictionaries that do not belong to any categories.\n"
		"Download all categories (including 0) by default.",
		metavar="CATEGORY",
	)
	parser.add_argument(
		"--skip-categories",
		"-s",
		default=[],
		nargs="+",
		help="Skip downloading existent categories specified in the argument. Subcategories are not considered.\n"
		"Only skip downloading existent dictionaries by default.\n",
		metavar="CATEGORY",
	)
	parser.add_argument(
		"--concurrent-downloads",
		"-j",
		default=os.cpu_count() * 2,
		type=int,
		help="Set the number of parallel downloads.\n" "Default: os.cpu_count() * 2",
		metavar="N",
	)
	parser.add_argument(
		"--max-retries",
		"-m",
		default=5,
		type=int,
		help="Set the maximum number of retries.\n" "Default: 5",
		metavar="N",
	)
	parser.add_argument(
		"--timeout",
		"-t",
		default=60,
		type=float,
		help="Set timeout in seconds.\n" "Default: 60",
		metavar="SEC",
	)
	parser.add_argument(
		"--verbose",
		"-v",
		action=argparse.BooleanOptionalAction,
		default=False,
		help="Verbose output.\n" "Default: False",
	)
	parser.add_argument(
		"--keep-going",
		"-k",
		action=argparse.BooleanOptionalAction,
		default=False,
		help="Continue as much as possible after an error.\n" "Default: False",
	)
	args = parser.parse_args()
	with SougouSpider(
		args.directory,
		args.skip_categories,
		args.concurrent_downloads,
		args.max_retries,
		args.timeout,
		args.keep_going,
	) as SGSpider:
		logging.basicConfig(
			format="%(levelname)s:%(message)s",
			level=logging.INFO if args.verbose else logging.WARNING,
		)
		SGSpider.download_dicts(args.categories)

from bs4 import BeautifulSoup
import requests
from pathlib import Path
import argparse
import concurrent.futures


class SougouSpider:
	def __init__(self):
		self.headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:60.0) Gecko/20100101 Firefox/60.0",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
			"Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
			"Accept-Encoding": "gzip, deflate",
			"Connection": "keep-alive",
		}

	def get_html(self, url):
		try:
			session = requests.Session()
			session.mount("https://", requests.adapters.HTTPAdapter(max_retries=5))
			return session.get(url, headers=self.headers, timeout=5)
		except requests.exceptions.Timeout as e:
			print(e)

	def download(self, name, url, category_path):
		file_path = category_path / (name + ".scel")
		if file_path.is_file():
			print(f"{file_path} already exists, skipping...")
		else:
			file_path.write_bytes(self.get_html(url).content)
			print(f"{file_path.name} download succeeded.")

	def get_download_links(self, category_url, page, category_path):
		download_urls = {}
		for dict_td_list in BeautifulSoup(
			self.get_html(category_url + "/default/" + str(page)).text,
			"html.parser",
		).find_all("div", class_="dict_detail_block"):
			key_download = dict_td_list.find("div", class_="detail_title").a
			download_urls[
				# For dictionaries like 天线行业/BSA
				key_download.string.replace("/", "-")
				.replace(",", "-")
				.replace("|", "-")
				.replace("\\", "-")
				.replace("'", "-")
				if key_download.string
				# For dictionaries without a name like index 15946
				else BeautifulSoup(
					self.get_html(
						"https://pinyin.sogou.com" + key_download["href"]
					).text,
					"html.parser",
				)
				.find("div", class_="dict_info_str")
				.string
			] = dict_td_list.find("div", class_="dict_dl_btn").a["href"]
		return download_urls, category_path

	def download_dicts(self, save_path, categories=None, skip_category=False):
		save_path.mkdir(parents=True, exist_ok=True)
		if categories is None:
			categories = ["0"]
			for dict_nav_list in BeautifulSoup(
				self.get_html("https://pinyin.sogou.com/dict/cate/index/1").text,
				"html.parser",
			).find_all("li", class_="nav_list"):
				categories.append(dict_nav_list.a["href"].split("/")[-1])
		with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
			result_futures = []
			for category in categories:
				category_path = save_path / category
				if category_path.is_dir() and skip_category:
					print(f"Category {category} already exists, skipping...")
					continue
				category_path.mkdir(exist_ok=True)
				# For dictionaries that do not belong to any categories
				if category == "0":
					executor.submit(
						self.download,
						"网络流行新词【官方推荐】",
						"https://pinyin.sogou.com/d/dict/download_cell.php?id=4&name=网络流行新词【官方推荐】",
						category_path,
					)
					for dict_td_list in BeautifulSoup(
						self.get_html(
							"https://pinyin.sogou.com/dict/detail/index/4"
						).text,
						"html.parser",
					).find_all("div", class_="rcmd_dict"):
						executor.submit(
							self.download,
							dict_td_list.find("div", class_="rcmd_dict_title").a.string,
							"https:"
							+ dict_td_list.find("div", class_="rcmd_dict_dl_btn").a[
								"href"
							],
							category_path,
						)
				else:
					category_urls = []
					# Category 167 does not have a real page
					if category == "167":
						for dict_td_list in BeautifulSoup(
							self.get_html(
								"https://pinyin.sogou.com/dict/cate/index/180"
							).text,
							"html.parser",
						).find_all("div", class_="citylistcate"):
							category_urls.append(
								"https://pinyin.sogou.com" + dict_td_list.a["href"]
							)
					else:
						category_urls.append(
							"https://pinyin.sogou.com/dict/cate/index/" + category
						)
					for category_url in category_urls:
						pages = (
							BeautifulSoup(
								self.get_html(category_url).text, "html.parser"
							)
							.find("div", id="dict_page_list")
							.find_all("a")
						)
						page_n = 2 if len(pages) < 2 else int(pages[-2].string) + 1
						result_futures += [
							executor.submit(
								self.get_download_links,
								category_url,
								page,
								category_path,
							)
							for page in range(1, page_n)
						]
			for future in concurrent.futures.as_completed(result_futures):
				try:
					download_urls, category_path = future.result()
					for name, url in download_urls.items():
						executor.submit(self.download, name, url, category_path)
				except Exception as e:
					print(e)


def check_category_index(value):
	if not value.isdigit():
		raise argparse.ArgumentTypeError(
			"The index of a category must be a non-negative integer"
		)
	return value


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
		help="The directory to save dictionaries, which are divided by categories in DIR.\n"
		"The default directory is sougou_dict.",
		metavar="DIR",
	)
	parser.add_argument(
		"--categories",
		"-c",
		nargs="+",
		type=check_category_index,
		help="List of category indexes (must be non-negative integers) to be downloaded.\n"
		"Special category index 0 is for dictionaries that do not belong to any categories.\n"
		"Download all categories (including 0) by default.",
		metavar="CATEGORY",
	)
	parser.add_argument(
		"--skip-category",
		action=argparse.BooleanOptionalAction,
		default=False,
		help="Skip downloading entire category if the directory exists. Subcategories are not considered.\n"
		"Only skip downloading single dictionary if the file exists by default.",
	)
	args = parser.parse_args()
	SGSpider = SougouSpider()
	SGSpider.download_dicts(
		args.directory,
		None if args.categories is None else list(set(args.categories)),
		args.skip_category,
	)

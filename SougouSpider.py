from bs4 import BeautifulSoup
import requests
import os
import argparse


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

	def download(self, download_urls, category_path):
		cnt = 0
		for key_download, url_download in download_urls.items():
			file_path = category_path + "/" + key_download + ".scel"
			if os.path.exists(file_path):
				print(f"{key_download}.scel already exists, skipping...")
			else:
				with open(file_path, "wb") as fw:
					fw.write(self.get_html(url_download).content)
					print(f"{key_download}.scel download succeeded.")
					cnt += 1
		return cnt

	def download_dicts(self, save_path, categories=None, skip_category=False):
		if not os.path.exists(save_path):
			try:
				os.mkdir(save_path)
			except Exception as e:
				print(e)
		if not categories:
			categories = ["0"]
			for dict_nav_list in BeautifulSoup(
				self.get_html("https://pinyin.sogou.com/dict/cate/index/1").text,
				"html.parser",
			).find_all("li", class_="nav_list"):
				categories.append(dict_nav_list.a["href"].split("/")[-1])
		cnt = 0
		for category in categories:
			category_path = save_path + "/" + category
			if not os.path.exists(category_path):
				try:
					os.mkdir(category_path)
				except Exception as e:
					print(e)
			elif skip_category:
				print(f"Category {category} already exists, skipping...")
				continue
			if category == "0":  # For dictionaries that do not belong to any categories
				download_urls = {
					"网络流行新词【官方推荐】": "https://pinyin.sogou.com/d/dict/download_cell.php?id=4&name=网络流行新词【官方推荐】"
				}
				for dict_td_list in BeautifulSoup(
					self.get_html("https://pinyin.sogou.com/dict/detail/index/4").text,
					"html.parser",
				).find_all("div", class_="rcmd_dict"):
					download_urls[
						dict_td_list.find("div", class_="rcmd_dict_title").a.string
					] = (
						"https:"
						+ dict_td_list.find("div", class_="rcmd_dict_dl_btn").a["href"]
					)
				cnt += self.download(download_urls, category_path)
			else:
				if category == "167":  # Category 167 does not have a real page
					category_urls = []
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
					category_urls = [
						"https://pinyin.sogou.com/dict/cate/index/" + category
					]
				for category_url in category_urls:
					pages = (
						BeautifulSoup(self.get_html(category_url).text, "html.parser")
						.find("div", id="dict_page_list")
						.find_all("a")
					)
					page_n = 2 if len(pages) < 2 else int(pages[-2].string) + 1
					for page in range(1, page_n):
						download_urls = {}
						for dict in BeautifulSoup(
							self.get_html(category_url + "/default/" + str(page)).text,
							"html.parser",
						).find_all("div", class_="dict_detail_block"):
							key_download = dict.find("div", class_="detail_title").a
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
										"https://pinyin.sogou.com"
										+ key_download["href"]
									).text,
									"html.parser",
								)
								.find("div", class_="dict_info_str")
								.string
							] = dict.find("div", class_="dict_dl_btn").a["href"]
						cnt += self.download(download_urls, category_path)
		print(f"Total download: {cnt} dictionaries.")


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
		help="The directory to save dictionaries, which are divided by categories in DIR.\n"
		"The default directory is sougou_dict.",
		metavar="DIR",
	)
	parser.add_argument(
		"--category",
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
	SGSpider.download_dicts(args.directory, args.category, args.skip_category)

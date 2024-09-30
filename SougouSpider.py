from bs4 import BeautifulSoup
from urllib.parse import unquote
import requests
import re
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

	def GetHtml(self, url):
		try:
			session = requests.Session()
			session.mount("https://", requests.adapters.HTTPAdapter(max_retries=5))
			return session.get(url, headers=self.headers, timeout=5)
		except requests.exceptions.Timeout as e:
			print(e)

	def Download(self, downloadUrls, categoryPath):
		for keyDownload, urlDownload in downloadUrls.items():
			filePath = categoryPath + "/" + keyDownload + ".scel"
			if os.path.exists(filePath):
				print(keyDownload + " already exists, skipping...")
			else:
				with open(filePath, "wb") as fw:
					fw.write(self.GetHtml(urlDownload).content)
					print(keyDownload + " download succeeded.")

	def DownloadDicts(self, savePath, categories=None):
		if not os.path.exists(savePath):
			try:
				os.mkdir(savePath)
			except Exception as e:
				print(e)
		if not categories:
			categories = []
			for dict_nav_list in BeautifulSoup(
				self.GetHtml("https://pinyin.sogou.com/dict/cate/index/1").text,
				"html.parser",
			).find_all("li", class_="nav_list"):
				categories.append(dict_nav_list.a["href"].split("/")[-1])
		for category in categories:
			categoryPath = savePath + "/" + category
			if not os.path.exists(categoryPath):
				try:
					os.mkdir(categoryPath)
				except Exception as e:
					print(e)
			if category == "0":
				downloadUrls = {
					"网络流行新词【官方推荐】": "https://pinyin.sogou.com/d/dict/download_cell.php?id=4&name=网络流行新词【官方推荐】"
				}
				for dict_td_list in BeautifulSoup(
					self.GetHtml("https://pinyin.sogou.com/dict/detail/index/4").text,
					"html.parser",
				).find_all("div", class_="rcmd_dict"):
					downloadUrls[
						dict_td_list.find("div", class_="rcmd_dict_title").a.string
					] = (
						"https:"
						+ dict_td_list.find("div", class_="rcmd_dict_dl_btn").a["href"]
					)
				self.Download(downloadUrls, categoryPath)
			else:
				if category == "167":
					categoryUrls = []
					for dict_td_list in BeautifulSoup(
						self.GetHtml(
							"https://pinyin.sogou.com/dict/cate/index/180"
						).text,
						"html.parser",
					).find_all("div", class_="citylistcate"):
						categoryUrls.append(
							"https://pinyin.sogou.com" + dict_td_list.a["href"]
						)
				else:
					categoryUrls = [
						"https://pinyin.sogou.com/dict/cate/index/" + category
					]
				for categoryUrl in categoryUrls:
					for page in range(
						1,
						int(
							BeautifulSoup(self.GetHtml(categoryUrl).text, "html.parser")
							.find("div", id="dict_page_list")
							.find_all("a")[-2]
							.string
						)
						+ 1,
					):
						downloadUrls = {}
						for dict_dl_list in BeautifulSoup(
							self.GetHtml(categoryUrl + "/default/" + str(page)).text,
							"html.parser",
						).find_all("div", class_="dict_dl_btn"):
							dict_dl_url = dict_dl_list.a["href"]
							downloadUrls[
								unquote(
									re.compile(r"name=(.*)").findall(dict_dl_url)[0],
									"utf-8",
								)
								.replace("/", "-")
								.replace(",", "-")
								.replace("|", "-")
								.replace("\\", "-")
								.replace("'", "-")
							] = dict_dl_url
						self.Download(downloadUrls, categoryPath)


def check_valid_category_index(value):
	if not value.isnumeric() or int(value) < 0:
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
		"--path", "-p", default="sougou_dict", help="The path to save dictionaries", metavar="PATH"
	)
	parser.add_argument(
		"--categories",
		"-c",
		nargs="+",
		type=check_valid_category_index,
		help="The indexes of categories of dictionaries to be downloaded. Must be a non-negative integer.\n"
		"Special index 0 is for dictionaries that do not belong to any categories",
		metavar="CATEGORY",
	)
	args = parser.parse_args()
	SGSpider = SougouSpider()
	SGSpider.DownloadDicts(args.path, args.categories)

all: build

build: build_fcitx

build_fcitx: sougou.dict baidu.dict

build_rime: sougou.dict.yaml baidu.dict.yaml

sougou.source.fcitx:
	test -d sougou_dict || { echo The sougou_dict folder does not exist!; exit 1; }
	ImeWlConverterCmd -i:scel sougou_dict -o:libimetxt sougou.source.fcitx

sougou.source.rime:
	test -d sougou_dict || { echo The sougou_dict folder does not exist!; exit 1; }
	ImeWlConverterCmd -i:scel sougou_dict -o:rime sougou.source.rime

sougou.dict: sougou.source.fcitx
	sed -i -e 's/lue/lve/g' -e 's/nue/nve/g' sougou.source.fcitx # Temp fix for https://github.com/studyzy/imewlconverter/issues/328
	libime_pinyindict sougou.source.fcitx sougou.dict

sougou.dict.yaml: sougou.source.rime
	printf -- '---\nname: sougou\nversion: "0.1"\nsort: by_weight\n...\n' > sougou.dict.yaml
	cat sougou.source.rime >> sougou.dict.yaml

baidu.source.fcitx:
	test -d baidu_dict || { echo The baidu_dict folder does not exist!; exit 1; }
	ImeWlConverterCmd -i:bdpy baidu_dict -o:libimetxt baidu.source.fcitx

baidu.source.rime:
	test -d baidu_dict || { echo The baidu_dict folder does not exist!; exit 1; }
	ImeWlConverterCmd -i:bdpy baidu_dict -o:rime baidu.source.rime

baidu.dict: baidu.source.fcitx
	sed -i -e 's/lue/lve/g' -e 's/nue/nve/g' baidu.source.fcitx # Temp fix for https://github.com/studyzy/imewlconverter/issues/328
	libime_pinyindict baidu.source.fcitx baidu.dict

baidu.dict.yaml: baidu.source.rime
	printf -- '---\nname: baidu\nversion: "0.1"\nsort: by_weight\n...\n' > baidu.dict.yaml
	cat baidu.source.rime >> baidu.dict.yaml

install: install_fcitx

install_fcitx: install_sougou_dict install_baidu_dict

install_rime: install_sougou_dict_yaml install_baidu_dict_yaml

install_sougou_dict: sougou.dict
	install -Dm644 sougou.dict -t $(DESTDIR)/usr/share/fcitx5/pinyin/dictionaries/

install_sougou_dict_yaml: sougou.dict.yaml
	install -Dm644 sougou.dict.yaml -t $(DESTDIR)/usr/share/rime-data/

install_baidu_dict: baidu.dict
	install -Dm644 baidu.dict -t $(DESTDIR)/usr/share/fcitx5/pinyin/dictionaries/

install_baidu_dict_yaml: baidu.dict.yaml
	install -Dm644 baidu.dict.yaml -t $(DESTDIR)/usr/share/rime-data/

clean:
	rm -f sougou.source.fcitx sougou.source.rime sougou.dict sougou.dict.yaml \
		baidu.source.fcitx baidu.source.rime baidu.dict baidu.dict.yaml

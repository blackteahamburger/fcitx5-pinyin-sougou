all: build

build: sougou.dict

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

install: sougou.dict
	install -Dm644 sougou.dict -t $(DESTDIR)/usr/share/fcitx5/pinyin/dictionaries/

install_rime_dict: sougou.dict.yaml
	install -Dm644 sougou.dict.yaml -t $(DESTDIR)/usr/share/rime-data/

clean:
	rm -f sougou.source.fcitx sougou.source.rime sougou.dict sougou.dict.yaml

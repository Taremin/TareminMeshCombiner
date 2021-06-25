# Taremin Mesh Combiner

## なにこれ？

Taremin が Blender を使う上で便利そうな機能を詰め込んだ Blender addon です。
主に FBX 出力する前にメッシュオブジェクトのモディファイアを適用して結合するための機能を揃えています。
具体的な機能は以下のとおりです。

- アクティブなメッシュオブジェクトに結合
- 非表示のメッシュオブジェクトの削除
- 結合したくないオブジェクトは結合しない
- 結合時に事前に設定した頂点に対して重複頂点の結合を行う
- 衣装を変えたときに(アーマチュアレイヤーで選択されていない)不必要なボーンを消す


## インストール

zip ファイルをダウンロードして、「ファイル」「ユーザー設定」「アドオン」「ファイルからアドオンをインストール」を選択し、ダウンロードした zip ファイルをインストールします。

![ダウンロード方法](images/how_to_download.png)

3D View: Taremin Blender Plugin という項目がアドオン一覧に追加されるのでチェックボックスをオンにします。


## 使い方

![ツールパネル](images/toolpanel.png)

3Dビューのときに左のツールパネルに "Taremin" という項目が追加されているので選択します。
(Blender2.8ではツールパネルへのアドオンでの追加が禁止になったので右のサイドバーに追加されます)

![結合先のオブジェクトをアクティブにする](images/activate_mesh_object.png)

結合先のオブジェクトをアクティブにして "最適化" ボタンを押すと、オブジェクトが結合されて非表示状態のオブジェクトやFBX出力に不必要なオブジェクトが削除されます。

### シェイプキーを持つオブジェクトがある場合

Blenderではシェイプキーを持つオブジェクトはモディファイアを適用することができません。
そこで [Apply Modifier アドオン](https://sites.google.com/site/matosus304blendernotes/home/download) がインストールされている場合、このアドオンを使って適用します。

### グループ化

正規表現とコレクションによるグループ化によって、例えば服装やアクセサリなど複数のオブジェクトに結合することができます。
正規表現によるグループ化は元のオブジェクト名を **置換して** 結合先のオブジェクト名にすることができ、その際に後方参照も利用することが出来ます。

例：名前に `帽子` を含むオブジェクトを `帽子` オブジェクトに結合

```
正規表現: .*(帽子).*
オブジェクト名:\1
```

ここで `帽子` を `.*` で囲っているのは、上述の通りオブジェクト名の置換を行うため前後の文字列を削除するためです。

利用可能な正規表現の詳しい説明については [Python3 の re モジュールのリファレンス](https://docs.python.org/ja/3/library/re.html) を参照してください。


### 結合後に重複頂点の削除を行いたい場合

首から上を身体から分離している場合など、結合後に "重複頂点の削除" で結合を行いたい場合があります。
その場合、"重複頂点の削除" の対象としたい頂点で頂点グループを作成し、その名前の先頭に "Merge." を付けます。
結合処理後に "Merge." の付いてる頂点グループに対して自動的に "重複頂点の削除" が実行されます。


## 更新履歴

- 0.1.0
  - Blender2.7系列のサポート終了(2.93以降からは2.7系列との互換性が失われるため)
  - 正規表現とコレクションによるグループ化機能の追加
    - それに伴い `.NoMerge` で結合対象から外れる仕様の廃止
  - 
- 0.0.7
  - Blender2.8 への対応
  - オブジェクトモードでないときやメッシュを選択してないときは実行できないUIに変更
- 0.0.6: アーマチュアボーンを削除するときに親がある場合は頂点ウェイトの引き継ぎをするように変更
- 0.0.5:
  - "Merge."から始まる頂点グループをオブジェクト結合後に重複頂点の削除をする機能を追加
  - ".NoMerge" で終わるオブジェクトはオブジェクト結合の対象外にするように変更
  - アーマチュアが非表示のときに正常に処理ができないバグの修正
- 0.0.4: 非選択アーマチュアレイヤーのボーン削除機能を追加、UVマップのリネーム時、マテリアルのテクスチャスロットもリネームするように修正
- 0.0.3: シェイプキーを設定しているオブジェクトがある場合 Apply Modifier アドオンを使って適用
- 0.0.2: 非表示レイヤーのオブジェクト削除オプションを追加
- 0.0.1: 初期実装

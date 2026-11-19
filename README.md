# L.C.a.X.s.

**Layer Tree State Restorer**

**L**ayer **C**ollapse **a**nd e**X**pansion **s**tate

L.C.a.X.s. works around a QGIS layer-tree expansion bug. When a project opens,
QGIS selects the first layer and can expand its parent groups even when the
project saved them as collapsed. After project loading finishes, L.C.a.X.s.
restores the saved expanded and collapsed states of groups and layer legends.

## Always open

A group can be explicitly kept open from its context menu:

- Right-click a group and choose **L.C.a.X.s. > Always open**
- Choose **L.C.a.X.s. > Follow saved state** to remove the override
- An always-open group also opens its ancestor groups so that it is visible
- The setting is stored in the QGIS project on the group itself

L.C.a.X.s. has no toolbar button or settings window. It does not change layer
visibility, drawing order, or the active layer. It supports QGS and QGZ
projects, and captures project-storage documents through the QGIS project-read
signal.

## 日本語

L.C.a.X.s.は、QGIS起動時のレイヤーツリー自動展開Bugを回避する
**レイヤーツリー状態復元プラグイン**です。

QGISはプロジェクトを開いた後に先頭レイヤーを選択するため、閉じた状態で
保存された親グループが展開されることがあります。L.C.a.X.s.は読込完了後、
プロジェクトに保存されたグループとレイヤー凡例の展開・折りたたみ状態を
復元します。

グループの右クリックメニューでは、次の動作を選択できます。

- **L.C.a.X.s. > 常に開く**：指定グループとその祖先を起動後に開きます
- **L.C.a.X.s. > 保存状態に従う**：「常に開く」を解除します

ツールバーボタンや設定画面はありません。レイヤーの可視性、描画順序、
選択レイヤーは変更しません。

## Development check

```bash
PYTHONPYCACHEPREFIX=/tmp/lcaxs_pycache \
  python3 -m py_compile __init__.py plugin.py state.py
QT_QPA_PLATFORM=offscreen \
PYTHONPATH=..:/usr/share/qgis/python:/usr/share/qgis/python/plugins \
  python3 -B -m unittest discover -s tests
```

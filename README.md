# 文献管理

一个 Windows 桌面端文献管理工具，用 Python + Qt 编写。支持拖入论文文件、自动读取 PDF 题名、DOI、摘要、期刊和出版社信息，并可按分类管理、导出表格。

## 功能

- 拖入 PDF、Word、TXT、RIS、BibTeX 文件添加文献
- 自动复制论文到指定论文目录
- 自动读取 PDF 题名、DOI、摘要、期刊、出版社
- 题名、DOI、摘要、期刊、出版社、分类、备注都可以手动修改
- 左侧分类列表支持筛选和拖动文献改分类
- 支持多选删除、多选改分类
- 表格列可显示/隐藏/调整顺序
- 右键定位论文文件或使用 Windows 打开方式
- 导出 CSV 和 Markdown

## 运行

建议使用 Conda 或普通 Python 虚拟环境。

```powershell
pip install -r requirements.txt
python reference_manager_qt.py
```

也可以在 Windows 下双击：

```text
Start Reference Manager Qt.cmd
```

## 打包

安装依赖后，在 Windows 下双击：

```text
Build Reference Manager.cmd
```

打包结果位于：

```text
dist\ReferenceManager
```

分享给别人时应发送整个 `dist\ReferenceManager` 文件夹，而不是只发送单独的 exe。

## 数据目录

程序运行时会在本地生成：

```text
_reference_manager_qt
```

其中包含数据库、论文文件、列设置和导出文件。该目录是用户数据，不应提交到 GitHub。


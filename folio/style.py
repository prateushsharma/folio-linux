"""Folio-Linux design tokens and application-wide Qt styles."""

STYLE = r"""
* { font-family: 'Inter', 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 13px; }
QWidget#Root { background: #f7f5f1; color: #242d36; }
QWidget#HomeSurface { background: #f7f5f1; }
QFrame#Sidebar { background: #202c38; border: none; }
QFrame#ReaderRail { background: #202c38; border: none; }
QLabel#Logo { font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: 1px; }
QLabel#LogoSubtitle { color: #aab8c6; font-size: 10px; letter-spacing: 2px; }
QLabel#SidebarSection { color: #8294a4; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QPushButton#SidebarButton { text-align: left; color: #d3dce2; padding: 12px 15px;
  background: transparent; border: 0; border-radius: 10px; font-weight: 600; }
QPushButton#SidebarButton:hover { background: #344455; color: #ffffff; }
QPushButton#SidebarButton[active="true"] { background: #c57751; color: #ffffff; }
QPushButton#RailButton { color: #b5c1cb; background: transparent; border: none; border-radius: 11px;
  font-size: 19px; min-height: 44px; }
QPushButton#RailButton:hover { background: #354654; color: white; }
QPushButton#RailButton[active="true"] { background: #bd744f; color: #ffffff; }
QLabel#Eyebrow { color: #b46d4b; font-weight: 750; letter-spacing: 1.5px; font-size: 11px; }
QLabel#HugeTitle { color: #273543; font-size: 37px; font-weight: 800; }
QLabel#SectionTitle { color: #293645; font-size: 22px; font-weight: 800; }
QLabel#Subtitle { color: #71808b; font-size: 13px; }
QFrame#Hero { border: 1px solid #e4d7cd; border-radius: 20px;
  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #fff1e5,stop:1 #f5d9c4); }
QLabel#HeroTitle { font-size: 27px; font-weight: 800; color: #513b33; }
QLabel#HeroText { font-size: 13px; color: #795f55; }
QFrame#BookCard { background: #fffefa; border: 1px solid #e8e5e0; border-radius: 16px; }
QFrame#BookCard:hover { border: 1px solid #c7aa91; background: #ffffff; }
QLabel#CardTitle { font-size: 13px; font-weight: 740; color: #30404d; }
QLabel#CardSub { color: #82909a; font-size: 11px; }
QProgressBar#CardProgress { min-height: 5px; max-height: 5px; border: 0; border-radius: 2px; background: #ede8e3; }
QProgressBar#CardProgress::chunk { background: #c77b51; border-radius: 2px; }
QPushButton#PrimaryButton { background: #b96e49; color: white; border-radius: 10px;
  padding: 11px 19px; font-weight: 750; border: 0; }
QPushButton#PrimaryButton:hover { background: #a85d3e; }
QPushButton#SecondaryButton { background: #fff; color: #465462; border: 1px solid #e0e1df;
  border-radius: 10px; padding: 10px 16px; font-weight: 650; }
QPushButton#SecondaryButton:hover { border: 1px solid #c58f72; }
QLineEdit#SearchBox { padding: 10px 15px; border-radius: 12px; border: 1px solid #e3e3df;
  background: white; color: #2b3845; selection-background-color: #c77b51; }
QLineEdit#SearchBox:focus { border: 1px solid #c77b51; }
QFrame#ReaderBar { background: #fffefa; border-bottom: 1px solid #e5e3de; }
QFrame#BottomBar { background: #fffefa; border-top: 1px solid #e5e3de; }
QLabel#ReaderTitle { color: #33404a; font-size: 14px; font-weight: 750; }
QLabel#Muted { color: #7b8791; font-size: 12px; }
QPushButton#IconButton { border: 0; border-radius: 9px; color: #52616f; background: transparent;
  min-width: 31px; min-height: 32px; font-size: 16px; }
QPushButton#IconButton:hover { background: #f1ede7; color: #a95b3a; }
QPushButton#SegmentButton { border: 1px solid #e5e2dc; border-radius: 9px; color: #677682;
  background: #f8f7f4; padding: 8px 12px; font-size: 12px; font-weight: 650; }
QPushButton#SegmentButton[active="true"] { color: #a75e3e; background: #fff0e6; border: 1px solid #e5b9a3; }
QFrame#SidePanel { background: #fffcf7; border-left: 1px solid #e9e4dc; }
QLabel#PanelTitle { font-size: 19px; font-weight: 800; color: #2e3c4b; }
QPushButton#PanelTab { background: transparent; color: #71808c; border: 0;
  border-bottom: 2px solid transparent; padding: 10px 6px; font-weight: 650; }
QPushButton#PanelTab[active="true"] { color: #b66b48; border-bottom: 2px solid #bd744f; }
QListWidget, QTreeWidget { background: transparent; border: none; color: #3c4b57;
  outline: 0; padding: 5px; }
QListWidget::item, QTreeWidget::item { padding: 10px 6px; border-radius: 6px; }
QListWidget::item:selected, QTreeWidget::item:selected { background: #f4e4d9; color: #8f4a30; }
QListWidget::item:hover, QTreeWidget::item:hover { background: #f4eee8; }
QComboBox { border: 1px solid #e4e1dc; border-radius: 8px; padding: 7px; color: #455564; background: white; }
QMenu { background: #fffefc; color: #3b4b57; border: 1px solid #ddd8d2; padding: 7px; }
QMenu::item { padding: 9px 25px; border-radius: 5px; }
QMenu::item:selected { background: #f6e9de; color: #914629; }
QSlider::groove:horizontal { border-radius: 3px; height: 5px; background: #e7e1d9; }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; border-radius: 7px; background: #be744f; }
QScrollArea { background: transparent; border: 0; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #b6b9bc; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 9px; margin: 0; }
QScrollBar::handle:horizontal { background: #b6b9bc; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip { background: #243340; color: white; border: 0; padding: 7px; }
"""

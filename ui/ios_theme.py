# ui/ios_theme.py
# -*- coding: utf-8 -*-
"""
iOS风格主题配置
参考Apple Human Interface Guidelines设计规范
"""

# ========== 配色方案 ==========
# 基于iOS的浅色/深色模式配色

class IOSColors:
    """iOS风格配色"""

    # 主色调 - 蓝色系 (iOS默认蓝)
    PRIMARY = "#007AFF"
    PRIMARY_HOVER = "#0051D5"
    PRIMARY_PRESSED = "#004FC4"

    # 次要色调
    SECONDARY = "#5856D6"  # iOS紫色
    SUCCESS = "#34C759"    # iOS绿色
    WARNING = "#FF9500"    # iOS橙色
    DANGER = "#FF3B30"     # iOS红色

    # 背景色
    BG_PRIMARY = "#F5F5F7"      # iOS浅灰背景（调整为更柔和的灰色）
    BG_SECONDARY = "#FAFAFA"    # 卡片背景（改为极浅灰，避免纯白）
    BG_TERTIARY = "#F0F0F5"     # 更浅的背景
    BG_CARD = "#FAFAFA"         # 卡片专用背景
    BG_APP = "#E8E8ED"          # 应用底色（更深的灰）

    # 文字色
    TEXT_PRIMARY = "#000000"
    TEXT_SECONDARY = "#3C3C43"  # 次要文字
    TEXT_TERTIARY = "#8E8E93"   # 提示文字
    TEXT_PLACEHOLDER = "#C7C7CC"

    # 分割线
    SEPARATOR = "#E5E5EA"

    # 控件背景
    INPUT_BG = "#FFFFFF"
    INPUT_BORDER = "#D1D1D6"
    INPUT_BORDER_FOCUS = "#007AFF"

    # 阴影
    SHADOW_LIGHT = "#00000010"
    SHADOW_MEDIUM = "#00000020"


class IOSLayout:
    """iOS风格布局参数"""

    # 圆角半径
    CORNER_RADIUS_SMALL = 8
    CORNER_RADIUS_MEDIUM = 12
    CORNER_RADIUS_LARGE = 16
    CORNER_RADIUS_XLARGE = 20

    # 内边距
    PADDING_SMALL = 8
    PADDING_MEDIUM = 12
    PADDING_LARGE = 16
    PADDING_XLARGE = 20

    # 控件高度
    BUTTON_HEIGHT = 40
    BUTTON_HEIGHT_LARGE = 48
    INPUT_HEIGHT = 40
    TAB_HEIGHT = 52  # 导航栏高度（进一步增加）

    # 字体大小
    FONT_SIZE_SMALL = 11
    FONT_SIZE_NORMAL = 13
    FONT_SIZE_MEDIUM = 14
    FONT_SIZE_LARGE = 16
    FONT_SIZE_TITLE = 18
    FONT_SIZE_HEADING = 20
    FONT_SIZE_TAB = 16  # 导航栏字体大小（增大）
    FONT_SIZE_EDITOR = 15  # 编辑器字体大小（稍大）


class IOSFonts:
    """iOS风格字体配置"""

    # 优先使用系统字体，回退到微软雅黑
    FONT_FAMILY = "Microsoft YaHei"
    FONT_FAMILY_MONO = "Consolas"

    @staticmethod
    def get_font(size=13, weight="normal"):
        """获取字体配置"""
        if weight == "bold":
            return (IOSFonts.FONT_FAMILY, size, "bold")
        return (IOSFonts.FONT_FAMILY, size)

    @staticmethod
    def get_title_font(size=18):
        """获取标题字体"""
        return (IOSFonts.FONT_FAMILY, size, "bold")


# ========== CustomTkinter主题配置 ==========
def apply_ios_theme():
    """
    应用iOS风格主题到CustomTkinter
    返回主题配置字典
    """
    import customtkinter as ctk

    # 设置外观模式为浅色
    ctk.set_appearance_mode("light")

    # 设置默认颜色主题
    ctk.set_default_color_theme("blue")

    return {
        "fg_color": IOSColors.BG_SECONDARY,
        "bg_color": IOSColors.BG_PRIMARY,
        "border_color": IOSColors.SEPARATOR,
        "button_color": IOSColors.PRIMARY,
        "button_hover_color": IOSColors.PRIMARY_HOVER,
        "text_color": IOSColors.TEXT_PRIMARY,
    }


# ========== 组件样式预设 ==========
class IOSStyles:
    """iOS风格组件样式预设"""

    @staticmethod
    def card_frame():
        """卡片容器样式"""
        return {
            "fg_color": IOSColors.BG_CARD,
            "corner_radius": IOSLayout.CORNER_RADIUS_LARGE,
            "border_width": 0,
        }

    @staticmethod
    def primary_button():
        """主要按钮样式"""
        return {
            "fg_color": IOSColors.PRIMARY,
            "hover_color": IOSColors.PRIMARY_HOVER,
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "height": IOSLayout.BUTTON_HEIGHT,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_NORMAL, "bold"),
            "border_width": 0,
        }

    @staticmethod
    def secondary_button():
        """次要按钮样式"""
        return {
            "fg_color": IOSColors.BG_TERTIARY,
            "hover_color": IOSColors.SEPARATOR,
            "text_color": IOSColors.PRIMARY,
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "height": IOSLayout.BUTTON_HEIGHT,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_NORMAL),
            "border_width": 1,
            "border_color": IOSColors.SEPARATOR,
        }

    @staticmethod
    def success_button():
        """成功按钮样式（批量生成等）- 调整为更柔和的颜色"""
        return {
            "fg_color": "#30B050",  # 更柔和的绿色
            "hover_color": "#28A048",
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "height": IOSLayout.BUTTON_HEIGHT_LARGE,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_MEDIUM, "bold"),
            "border_width": 0,
        }

    @staticmethod
    def danger_button():
        """危险按钮样式"""
        return {
            "fg_color": IOSColors.DANGER,
            "hover_color": "#E52E24",
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "height": IOSLayout.BUTTON_HEIGHT,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_NORMAL, "bold"),
            "border_width": 0,
        }

    @staticmethod
    def input_entry():
        """输入框样式"""
        return {
            "fg_color": IOSColors.INPUT_BG,
            "border_color": IOSColors.INPUT_BORDER,
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "height": IOSLayout.INPUT_HEIGHT,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_NORMAL),
            "border_width": 1,
        }

    @staticmethod
    def textbox():
        """文本框样式 - 卡片式边框设计"""
        return {
            "fg_color": "#FFFFFF",  # 纯白背景
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_EDITOR),  # 使用较大字体
            "border_width": 1,
            "border_color": IOSColors.SEPARATOR,  # 使用分隔线颜色作为边框
        }

    @staticmethod
    def label_title():
        """标题标签样式"""
        return {
            "text_color": IOSColors.TEXT_PRIMARY,
            "font": IOSFonts.get_title_font(IOSLayout.FONT_SIZE_TITLE),
        }

    @staticmethod
    def label_normal():
        """普通标签样式"""
        return {
            "text_color": IOSColors.TEXT_SECONDARY,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_NORMAL),
        }

    @staticmethod
    def label_secondary():
        """次要标签样式"""
        return {
            "text_color": IOSColors.TEXT_TERTIARY,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_SMALL),
        }

    @staticmethod
    def progress_bar():
        """进度条样式"""
        return {
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "height": 8,
            "progress_color": IOSColors.PRIMARY,
            "fg_color": IOSColors.SEPARATOR,
        }

    @staticmethod
    def segmented_button():
        """分段按钮样式"""
        return {
            "fg_color": IOSColors.BG_TERTIARY,
            "selected_color": IOSColors.PRIMARY,
            "selected_hover_color": IOSColors.PRIMARY_HOVER,
            "unselected_color": IOSColors.BG_TERTIARY,
            "unselected_hover_color": IOSColors.SEPARATOR,
            "corner_radius": IOSLayout.CORNER_RADIUS_MEDIUM,
            "font": IOSFonts.get_font(IOSLayout.FONT_SIZE_NORMAL),
        }


# ========== 辅助函数 ==========
def create_card_frame(parent, **kwargs):
    """创建iOS风格卡片容器（带浅色背景和细微边框）"""
    import customtkinter as ctk
    style = {
        "fg_color": "#FFFFFF",  # 使用纯白卡片
        "corner_radius": IOSLayout.CORNER_RADIUS_LARGE,
        "border_width": 1,
        "border_color": IOSColors.SEPARATOR,  # 添加细微边框增强层次感
    }
    style.update(kwargs)
    return ctk.CTkFrame(parent, **style)


def create_section_title(parent, text, **kwargs):
    """创建章节标题"""
    import customtkinter as ctk
    style = IOSStyles.label_title()
    style.update(kwargs)
    return ctk.CTkLabel(parent, text=text, **style)

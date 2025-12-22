# ui/settings_tab.py
# -*- coding: utf-8 -*-
"""
Settings 标签页：整合所有配置项
- LLM Model settings
- Embedding settings
- Config choose
- Proxy setting
- WebDAV setting
"""
import customtkinter as ctk
from tkinter import messagebox
import os
import requests
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree as ET
import shutil
import time

from core.config.config_manager import load_config, save_config
from ui.ios_theme import IOSFonts
from ui.config_tab import (
    create_label_with_help,
    build_ai_config_tab,
    build_embeddings_config_tab,
    build_config_choose_tab
)


def build_settings_tab(self):
    """
    构建 Settings 标签页，整合所有配置
    使用 ScrollableFrame 包含多个配置区域，直接依次排列
    """
    self.settings_tab = self.tabview.add("设置")
    self.settings_tab.rowconfigure(0, weight=1)
    self.settings_tab.columnconfigure(0, weight=1)

    # 创建滚动容器
    scroll_container = ctk.CTkScrollableFrame(self.settings_tab)
    scroll_container.pack(fill="both", expand=True, padx=5, pady=5)
    scroll_container.columnconfigure(0, weight=1)

    row_idx = 0

    # ========== 1. LLM Model Settings ==========
    llm_title = ctk.CTkLabel(scroll_container, text="LLM Model Settings", font=IOSFonts.get_font(14, "bold"))
    llm_title.grid(row=row_idx, column=0, padx=10, pady=(15, 5), sticky="w")
    row_idx += 1

    llm_frame = ctk.CTkFrame(scroll_container, corner_radius=10, border_width=2, border_color="gray")
    llm_frame.grid(row=row_idx, column=0, padx=10, pady=(0, 10), sticky="ew")
    llm_frame.columnconfigure(0, weight=1)
    row_idx += 1

    # 将 llm_frame 作为 ai_config_tab 使用，保持兼容
    self.ai_config_tab = llm_frame
    self.config_frame = llm_frame  # 保持向后兼容
    build_ai_config_tab(self)

    # ========== 2. Embedding Settings ==========
    embedding_title = ctk.CTkLabel(scroll_container, text="Embedding Settings", font=IOSFonts.get_font(14, "bold"))
    embedding_title.grid(row=row_idx, column=0, padx=10, pady=(15, 5), sticky="w")
    row_idx += 1

    embedding_frame = ctk.CTkFrame(scroll_container, corner_radius=10, border_width=2, border_color="gray")
    embedding_frame.grid(row=row_idx, column=0, padx=10, pady=(0, 10), sticky="ew")
    embedding_frame.columnconfigure(0, weight=1)
    row_idx += 1

    self.embeddings_config_tab = embedding_frame
    build_embeddings_config_tab(self)

    # ========== 3. Config Choose ==========
    choose_title = ctk.CTkLabel(scroll_container, text="Config Choose", font=IOSFonts.get_font(14, "bold"))
    choose_title.grid(row=row_idx, column=0, padx=10, pady=(15, 5), sticky="w")
    row_idx += 1

    choose_frame = ctk.CTkFrame(scroll_container, corner_radius=10, border_width=2, border_color="gray")
    choose_frame.grid(row=row_idx, column=0, padx=10, pady=(0, 10), sticky="ew")
    choose_frame.columnconfigure(0, weight=1)
    row_idx += 1

    self.config_choose = choose_frame
    build_config_choose_tab(self)

    # ========== 4. Proxy Setting ==========
    proxy_title = ctk.CTkLabel(scroll_container, text="代理设置", font=IOSFonts.get_font(14, "bold"))
    proxy_title.grid(row=row_idx, column=0, padx=10, pady=(15, 5), sticky="w")
    row_idx += 1

    proxy_frame = ctk.CTkFrame(scroll_container, corner_radius=10, border_width=2, border_color="gray")
    proxy_frame.grid(row=row_idx, column=0, padx=10, pady=(0, 10), sticky="ew")
    proxy_frame.columnconfigure(1, weight=1)
    row_idx += 1

    build_proxy_section(self, proxy_frame)

    # ========== 5. WebDAV Setting ==========
    webdav_title = ctk.CTkLabel(scroll_container, text="WebDAV 设置", font=IOSFonts.get_font(14, "bold"))
    webdav_title.grid(row=row_idx, column=0, padx=10, pady=(15, 5), sticky="w")
    row_idx += 1

    webdav_frame = ctk.CTkFrame(scroll_container, corner_radius=10, border_width=2, border_color="gray")
    webdav_frame.grid(row=row_idx, column=0, padx=10, pady=(0, 10), sticky="ew")
    webdav_frame.columnconfigure(1, weight=1)
    row_idx += 1

    build_webdav_section(self, webdav_frame)


def build_proxy_section(self, parent):
    """
    构建 Proxy 配置区域
    """
    # 从配置文件加载代理设置
    proxy_setting = self.loaded_config.get("proxy_setting", {})

    # 代理启用开关
    create_label_with_help(self, parent, "启用代理:", "proxy_enabled", 0, 0)
    if not hasattr(self, 'proxy_enabled_var'):
        self.proxy_enabled_var = ctk.BooleanVar(value=proxy_setting.get("enabled", False))
    proxy_enabled_switch = ctk.CTkSwitch(
        parent,
        text="",
        variable=self.proxy_enabled_var,
        onvalue=True,
        offvalue=False,
        font=IOSFonts.get_font(12)
    )
    proxy_enabled_switch.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    # 地址输入框
    create_label_with_help(self, parent, "地址:", "proxy_address", 1, 0)
    if not hasattr(self, 'proxy_address_var'):
        self.proxy_address_var = ctk.StringVar(value=proxy_setting.get("proxy_url", "127.0.0.1"))
    proxy_address_entry = ctk.CTkEntry(parent, textvariable=self.proxy_address_var, font=IOSFonts.get_font(12))
    proxy_address_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    # 端口输入框
    create_label_with_help(self, parent, "端口:", "proxy_port", 2, 0)
    if not hasattr(self, 'proxy_port_var'):
        self.proxy_port_var = ctk.StringVar(value=proxy_setting.get("proxy_port", "10809"))
    proxy_port_entry = ctk.CTkEntry(parent, textvariable=self.proxy_port_var, font=IOSFonts.get_font(12))
    proxy_port_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

    def save_proxy_setting():
        """保存代理配置到JSON文件"""
        if "proxy_setting" not in self.loaded_config:
            self.loaded_config["proxy_setting"] = {}

        self.loaded_config["proxy_setting"]["enabled"] = self.proxy_enabled_var.get()
        self.loaded_config["proxy_setting"]["proxy_url"] = self.proxy_address_var.get()
        self.loaded_config["proxy_setting"]["proxy_port"] = self.proxy_port_var.get()

        try:
            save_config(self.loaded_config, self.config_file)
            messagebox.showinfo("提示", "代理配置已保存。")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {str(e)}")

        # 应用代理设置到环境变量
        if self.proxy_enabled_var.get():
            proxy_url = f"http://{self.proxy_address_var.get()}:{self.proxy_port_var.get()}"
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
        else:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)

    # 保存按钮
    save_btn = ctk.CTkButton(
        parent,
        text="保存代理设置",
        command=save_proxy_setting,
        font=IOSFonts.get_font(12)
    )
    save_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")


def build_webdav_section(self, parent):
    """
    构建 WebDAV 配置区域
    """
    # 初始化 WebDAV 配置
    if "webdav_config" not in self.loaded_config:
        self.loaded_config["webdav_config"] = {
            "webdav_url": "",
            "webdav_username": "",
            "webdav_password": ""
        }

    if not hasattr(self, 'webdav_url_var'):
        self.webdav_url_var = ctk.StringVar()
        self.webdav_username_var = ctk.StringVar()
        self.webdav_password_var = ctk.StringVar()

    self.webdav_url_var.set(self.loaded_config["webdav_config"].get("webdav_url", ""))
    self.webdav_username_var.set(self.loaded_config["webdav_config"].get("webdav_username", ""))
    self.webdav_password_var.set(self.loaded_config["webdav_config"].get("webdav_password", ""))

    def save_webdav_settings():
        self.loaded_config["webdav_config"]["webdav_url"] = self.webdav_url_var.get().strip()
        self.loaded_config["webdav_config"]["webdav_username"] = self.webdav_username_var.get().strip()
        self.loaded_config["webdav_config"]["webdav_password"] = self.webdav_password_var.get().strip()
        save_config(self.loaded_config, self.config_file)

    def test_webdav_connection(test=True):
        try:
            client = WebDAVClient(
                self.webdav_url_var.get().strip(),
                self.webdav_username_var.get().strip(),
                self.webdav_password_var.get().strip()
            )
            client.list_directory()
            if not test:
                save_webdav_settings()
                return True
            messagebox.showinfo("成功", "WebDAV 连接成功！")
            save_webdav_settings()
            return True
        except Exception as e:
            messagebox.showerror("错误", f"发生未知错误: {e}")
            return False

    def backup_to_webdav():
        try:
            target_dir = "AI_Novel_Generator"
            client = WebDAVClient(
                self.webdav_url_var.get().strip(),
                self.webdav_username_var.get().strip(),
                self.webdav_password_var.get().strip()
            )
            if not client.ensure_directory_exists(target_dir):
                client.create_directory(target_dir)
            client.upload_file(self.config_file, f"{target_dir}/config.json")
            messagebox.showinfo("成功", "配置备份成功！")
        except Exception as e:
            messagebox.showerror("错误", f"发生未知错误: {e}")
            return False

    def restore_from_webdav():
        try:
            target_dir = "AI_Novel_Generator"
            client = WebDAVClient(
                self.webdav_url_var.get().strip(),
                self.webdav_username_var.get().strip(),
                self.webdav_password_var.get().strip()
            )
            client.download_file(f"{target_dir}/config.json", self.config_file)
            self.loaded_config = load_config(self.config_file)
            messagebox.showinfo("成功", "配置恢复成功！")
        except Exception as e:
            messagebox.showerror("错误", f"发生未知错误: {e}")
            return False

    # WebDAV URL
    create_label_with_help(self, parent, "Webdav URL", "webdav_url", 0, 0, font=IOSFonts.get_font(12), sticky="w")
    dav_url_entry = ctk.CTkEntry(parent, textvariable=self.webdav_url_var, font=IOSFonts.get_font(12))
    dav_url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    # WebDAV 用户名
    create_label_with_help(self, parent, "Webdav用户名", "webdav_username", 1, 0, font=IOSFonts.get_font(12), sticky="w")
    dav_username_entry = ctk.CTkEntry(parent, textvariable=self.webdav_username_var, font=IOSFonts.get_font(12))
    dav_username_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    # WebDAV 密码
    create_label_with_help(self, parent, "Webdav密码", "webdav_password", 2, 0, font=IOSFonts.get_font(12), sticky="w")
    dav_password_entry = ctk.CTkEntry(parent, textvariable=self.webdav_password_var, font=IOSFonts.get_font(12), show="*")
    dav_password_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

    # 按钮组
    button_frame = ctk.CTkFrame(parent)
    button_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=10, sticky="ew")
    button_frame.columnconfigure((0, 1, 2), weight=1)

    test_btn = ctk.CTkButton(button_frame, text="测试连接", font=IOSFonts.get_font(12),
                            command=test_webdav_connection)
    test_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

    save_btn = ctk.CTkButton(button_frame, text="备份", font=IOSFonts.get_font(12),
                            command=backup_to_webdav)
    save_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    reset_btn = ctk.CTkButton(button_frame, text="恢复", font=IOSFonts.get_font(12),
                             command=restore_from_webdav)
    reset_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")


class WebDAVClient:
    """WebDAV 客户端（从 other_settings.py 复制）"""
    def __init__(self, base_url, username, password):
        """初始化WebDAV客户端"""
        self.base_url = base_url.rstrip('/') + '/'
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {
            'User-Agent': 'Python WebDAV Client',
            'Accept': '*/*'
        }
        self.ns = {'d': 'DAV:'}

    def _get_url(self, path):
        """获取完整的资源URL"""
        return self.base_url + path.lstrip('/')

    def list_directory(self):
        """列出目录（用于测试连接）"""
        url = self.base_url
        headers = self.headers.copy()
        headers['Depth'] = '1'
        response = requests.request('PROPFIND', url, headers=headers, auth=self.auth)
        response.raise_for_status()
        return True

    def directory_exists(self, path):
        """检查目录是否存在"""
        url = self._get_url(path)
        headers = self.headers.copy()
        headers['Depth'] = '0'
        try:
            response = requests.request('PROPFIND', url, headers=headers, auth=self.auth)
            if response.status_code == 207:
                root = ET.fromstring(response.content)
                res_type = root.find('.//d:resourcetype', namespaces=self.ns)
                if res_type is not None and res_type.find('d:collection', namespaces=self.ns) is not None:
                    return True
            return False
        except:
            return False

    def create_directory(self, path):
        """创建远程目录"""
        url = self._get_url(path)
        try:
            response = requests.request('MKCOL', url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            return True
        except:
            return False

    def ensure_directory_exists(self, path):
        """确保目录存在，如果不存在则创建"""
        path = path.rstrip('/')
        if self.directory_exists(path):
            return True
        parent_dir = os.path.dirname(path)
        if parent_dir and not self.directory_exists(parent_dir):
            if not self.ensure_directory_exists(parent_dir):
                return False
        return self.create_directory(path)

    def upload_file(self, local_path, remote_path):
        """上传文件到WebDAV服务器"""
        if not os.path.isfile(local_path):
            return False
        url = self._get_url(remote_path)
        try:
            with open(local_path, 'rb') as f:
                response = requests.put(url, data=f, auth=self.auth, headers=self.headers)
                response.raise_for_status()
            return True
        except:
            return False

    def download_file(self, remote_path, local_path):
        """从WebDAV服务器下载文件"""
        url = self._get_url(remote_path)
        local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), local_path)
        self.backup(local_path)
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, stream=True)
            response.raise_for_status()
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except:
            return False

    def backup(self, local_path):
        """备份本地文件"""
        if not os.path.exists(local_path):
            return
        name_parts = os.path.basename(local_path).rsplit('.', 1)
        base_name = name_parts[0]
        extension = name_parts[1] if len(name_parts) > 1 else ""
        timestamp = time.strftime("%Y%m%d%H%M%S")
        backup_dir = os.path.join(os.path.dirname(local_path), "backup")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        backup_file_name = f"{base_name}_{timestamp}_bak.{extension}"
        try:
            shutil.copy2(local_path, os.path.join(backup_dir, backup_file_name))
        except:
            pass


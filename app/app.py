from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from typing import Iterable

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
    Response,
    session,
)
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
UPLOAD_DIR = BASE_DIR / 'uploads'
BACKGROUND_DIR = DATA_DIR / 'site_backgrounds'
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
BACKGROUND_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'hamlog.db'
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'md', 'mp3', 'wav', 'm4a', 'ogg', 'zip', '7z', 'adif', 'adi'
}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
BING_CACHE: dict[str, object] = {'expires': 0, 'payload': None}

BAND_OPTIONS = [
    '2190m', '630m', '560m', '160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m',
    '8m', '6m', '5m', '4m', '2m', '1.25m', '70cm', '33cm', '23cm', '13cm', '9cm', '6cm', '3cm',
    '1.25cm', '6mm', '4mm', '2.5mm', '2mm', '1mm'
]
MODE_OPTIONS = [
    'AM', 'FM', 'NFM', 'WFM', 'SSB', 'LSB', 'USB', 'CW', 'RTTY', 'SSTV', 'PSK31', 'PSK63', 'FT8', 'FT4',
    'JT65', 'JT9', 'MSK144', 'FSK441', 'OLIVIA', 'DOMINO', 'MFSK', 'HELL', 'THOR', 'PACKET', 'APRS',
    'VARA', 'D-STAR', 'DMR', 'C4FM', 'P25', 'TETRA', 'FAX', 'ATV', 'DATV', 'ECHOLINK', 'FREEDV'
]

TRANSLATIONS = {
    'zh': {
        'site_title': 'HamLog', 'site_subtitle_admin': '本地通联日志管理', 'site_subtitle_public': '访客只读展示',
        'home': '首页', 'dashboard': '首页', 'qso': 'QSO', 'public_page': '访客页', 'adif': 'ADIF', 'appearance': '外观', 'account': '账户', 'settings': '设置', 'about': '说明', 'logout': '退出',
        'login_admin': '登录后台', 'theme_auto': '跟随系统', 'theme_light': '浅色', 'theme_dark': '深色',
        'appearance_title': '外观设置', 'appearance_desc': '可切换背景来源、纯色背景、透明度、主题模式，并切换中英文界面。', 'settings_title': '设置', 'settings_desc': '在这里统一管理界面、背景、主题、用户名与密码。',
        'background_source': '背景来源', 'current_background_source': '当前背景来源', 'bing_wallpaper': 'Bing 每日壁纸', 'upload_background': '自定义上传背景',
        'gradient_background': '仅使用渐变背景', 'solid_color_background': '纯色背景', 'save_background_source': '保存背景来源', 'upload_custom_background': '上传自定义背景',
        'choose_image': '选择图片', 'upload_and_enable': '上传并启用', 'background_opacity': '背景透明度', 'admin_bg_opacity': '后台页面背景透明度（0-100）',
        'public_bg_opacity': '访客页面背景透明度（0-100）', 'save_opacity': '保存透明度', 'return_dashboard': '返回控制台', 'solid_bg_color': '纯色背景颜色', 'save_solid_color': '保存纯色背景',
        'interface_language': '界面语言', 'save_language': '保存界面语言', 'theme_mode': '主题模式', 'save_theme_mode': '保存主题模式', 'chinese': '中文', 'english': 'English', 'not_uploaded': '未上传', 'about_title': '系统说明', 'about_desc': '本页面说明本地通联日志的用途、数据边界与合规使用要求。', 'about_system': '关于本系统', 'about_system_body': 'HamLog 是一个面向业余无线电爱好者的本地或自托管通联日志系统，用于记录、查询、导入导出 ADIF，并提供访客只读展示页。', 'about_usage': '使用说明', 'about_usage_body': '建议统一使用 UTC 记录通联时间，按实际 QSO 内容填写呼号、模式、波段、信号报告与备注；导入导出时优先采用 ADIF 以保证兼容性。', 'about_legal': '法律法规与合规提醒', 'about_legal_body': '在中国境内设置、使用业余无线电台，应遵守现行无线电管理法规和业余无线电台管理规定；仅可在核准频率、许可条件和操作权限范围内开展业余通信、技术研究与自我训练，不得用于营利活动，不得干扰正常无线电通信秩序。公网展示页面仅用于展示合法合规的通联记录，不应发布违法违规内容或敏感个人信息。', 'about_privacy': '隐私与公开展示', 'about_privacy_body': '如启用访客页或公网部署，请自行审查公开字段，避免暴露不必要的个人隐私、精确住址或未获授权的第三方信息。', 'about_disclaimer': '提示：本页面为通联日志管理与学习说明，不替代主管部门发布的正式法规文本。',
        'qso_log': 'QSO 日志', 'qso_log_desc': '采用紧凑视图，仅展示核心日志字段。', 'export_adif': '导出 ADIF', 'new_qso': '新增 QSO', 'callsign': '呼号', 'band': '波段', 'mode': '模式',
        'date_from': '起始日期', 'date_to': '结束日期', 'search': '查询', 'reset': '重置', 'import_adif': '导入 ADIF', 'my_callsign': '己方呼号', 'their_callsign': '对方呼号',
        'dxcc': 'DXCC', 'datetime': '日期时间', 'signal_report': '信号报告', 'comment': '备注', 'actions': '操作', 'expand': '展开', 'collapse': '收起', 'edit': '编辑', 'delete': '删除',
        'guest_log': '访客通联日志', 'guest_log_desc': '默认展示最近 10 条 QSO，仅展示核心日志字段；详情直接向下展开。', 'recent_ten': '最近十条 / 只读',
        'filter_hint': '访客页最多只展示最近 10 条匹配记录。', 'qso_record': 'QSO 记录', 'qso_record_desc': '按标准日志顺序填写，仅保留核心字段。', 'return_list': '返回列表', 'qso_date_utc': 'QSO 日期（UTC） *',
        'utc_time': 'UTC 时间 *', 'operator_callsign': '我方呼号', 'their_callsign_required': '对方呼号 *', 'frequency': '频率', 'rst_sent': 'RST 发', 'rst_recv': 'RST 收', 'their_qth': '对方 QTH', 'power_w': '功率 W', 'radio': '设备', 'antenna': '天线', 'comment_label': '备注 / COMMENT',
        'qsl_status': 'QSL 状态', 'qsl_sent': 'QSL 已寄出', 'qsl_sent_date': '寄出日期', 'qsl_received': 'QSL 已收到', 'qsl_received_date': '收到日期', 'yes': '是', 'no': '否', 'save': '保存', 'cancel': '取消', 'auto_utc_hint': '新建记录时自动填入当前 UTC；手动修改后即停止自动覆盖。',
        'login': '登录', 'username': '用户名', 'password': '密码', 'change_password': '修改密码', 'current_password': '当前密码', 'new_password': '新密码', 'confirm_password': '确认新密码', 'update_password': '更新密码', 'change_username': '修改用户名', 'current_username': '当前用户名', 'new_username': '新用户名 / 呼号', 'update_username': '更新用户名',
        'adif_import_title': '导入 ADIF', 'choose_adif': '选择 ADIF 文件', 'upload_file': '上传文件', 'dashboard_welcome': '欢迎回来', 'total_qsos': 'QSO 总数', 'pending_qsl': '待处理 QSL', 'attachments': '附件数量', 'recent_qsos': '最近通联', 'view_all': '查看全部', 'mode_stats': '模式统计',
        'na': 'N/A', 'none_match': '暂无匹配记录',
    },
    'en': {
        'site_title': 'HamLog', 'site_subtitle_admin': 'Local QSO Logbook', 'site_subtitle_public': 'Public Read-only View',
        'home': 'Home', 'dashboard': 'Home', 'qso': 'QSO', 'public_page': 'Public', 'adif': 'ADIF', 'appearance': 'Appearance', 'account': 'Account', 'settings': 'Settings', 'about': 'About', 'logout': 'Logout',
        'login_admin': 'Admin Login', 'theme_auto': 'Auto', 'theme_light': 'Light', 'theme_dark': 'Dark',
        'appearance_title': 'Appearance Settings', 'appearance_desc': 'Switch background source, solid color, opacity, theme mode, and UI language.', 'settings_title': 'Settings', 'settings_desc': 'Manage appearance, theme mode, background, username and password in one place.',
        'background_source': 'Background Source', 'current_background_source': 'Current background source', 'bing_wallpaper': 'Bing Daily Wallpaper', 'upload_background': 'Uploaded Background',
        'gradient_background': 'Gradient Only', 'solid_color_background': 'Solid Color', 'save_background_source': 'Save Background Source', 'upload_custom_background': 'Upload Custom Background',
        'choose_image': 'Choose Image', 'upload_and_enable': 'Upload and Enable', 'background_opacity': 'Background Opacity', 'admin_bg_opacity': 'Admin background opacity (0-100)',
        'public_bg_opacity': 'Public background opacity (0-100)', 'save_opacity': 'Save Opacity', 'return_dashboard': 'Back to Dashboard', 'solid_bg_color': 'Solid background color', 'save_solid_color': 'Save Solid Color',
        'interface_language': 'Interface Language', 'save_language': 'Save Language', 'theme_mode': 'Theme Mode', 'save_theme_mode': 'Save Theme Mode', 'chinese': '中文', 'english': 'English', 'not_uploaded': 'Not uploaded', 'about_title': 'About', 'about_desc': 'This page explains what the logbook is for, its data boundaries, and compliant use.', 'about_system': 'About this system', 'about_system_body': 'HamLog is a local or self-hosted amateur radio QSO logbook for recording contacts, querying records, importing/exporting ADIF, and offering a public read-only view.', 'about_usage': 'How to use it', 'about_usage_body': 'It is recommended to record QSO time in UTC and enter callsign, mode, band, signal report, and notes based on the actual contact. Prefer ADIF for data portability.', 'about_legal': 'Legal and compliance notice', 'about_legal_body': 'When setting up and using an amateur radio station in China, users should comply with current radio regulations and amateur station rules, operate only within authorized frequencies, licenses, and privileges, and must not use the station for profit or interfere with lawful radio communications. Public pages should display only lawful and appropriate log information.', 'about_privacy': 'Privacy and public display', 'about_privacy_body': 'If you enable the public page or deploy on the public Internet, review which fields are exposed and avoid disclosing unnecessary personal data, precise addresses, or unauthorized third-party information.', 'about_disclaimer': 'Note: this page is an operational guide and does not replace official legal texts issued by authorities.',
        'qso_log': 'QSO Log', 'qso_log_desc': 'Compact logbook view with essential fields only.', 'export_adif': 'Export ADIF', 'new_qso': 'New QSO', 'callsign': 'Callsign', 'band': 'Band', 'mode': 'Mode',
        'date_from': 'From Date', 'date_to': 'To Date', 'search': 'Search', 'reset': 'Reset', 'import_adif': 'Import ADIF', 'my_callsign': 'My Call', 'their_callsign': 'Call',
        'dxcc': 'DXCC', 'datetime': 'Date/Time', 'signal_report': 'RST', 'comment': 'Comment', 'actions': 'Actions', 'expand': 'Expand', 'collapse': 'Collapse', 'edit': 'Edit', 'delete': 'Delete',
        'guest_log': 'Public Logbook', 'guest_log_desc': 'Shows the latest 10 QSO records with inline details.', 'recent_ten': 'Latest 10 / Read-only',
        'filter_hint': 'The public page shows up to 10 matching records.', 'qso_record': 'QSO Entry', 'qso_record_desc': 'Use standard logbook order with essential fields only.', 'return_list': 'Back to List', 'qso_date_utc': 'QSO Date (UTC) *',
        'utc_time': 'UTC Time *', 'operator_callsign': 'My Callsign', 'their_callsign_required': 'Their Callsign *', 'frequency': 'Frequency', 'rst_sent': 'RST Sent', 'rst_recv': 'RST Rcvd', 'their_qth': 'Their QTH', 'power_w': 'Power W', 'radio': 'Radio', 'antenna': 'Antenna', 'comment_label': 'Comment',
        'qsl_status': 'QSL Status', 'qsl_sent': 'QSL Sent', 'qsl_sent_date': 'Sent Date', 'qsl_received': 'QSL Received', 'qsl_received_date': 'Received Date', 'yes': 'Yes', 'no': 'No', 'save': 'Save', 'cancel': 'Cancel', 'auto_utc_hint': 'New records auto-fill current UTC; manual edits stop auto-sync.',
        'login': 'Login', 'username': 'Username', 'password': 'Password', 'change_password': 'Change Password', 'current_password': 'Current Password', 'new_password': 'New Password', 'confirm_password': 'Confirm New Password', 'update_password': 'Update Password', 'change_username': 'Change Username', 'current_username': 'Current Username', 'new_username': 'New Username / Callsign', 'update_username': 'Update Username',
        'adif_import_title': 'Import ADIF', 'choose_adif': 'Choose ADIF File', 'upload_file': 'Upload File', 'dashboard_welcome': 'Welcome back', 'total_qsos': 'Total QSOs', 'pending_qsl': 'Pending QSL', 'attachments': 'Attachments', 'recent_qsos': 'Recent QSOs', 'view_all': 'View All', 'mode_stats': 'Mode Stats',
        'na': 'N/A', 'none_match': 'No matching records',
    }
}


DXCC_ENTITIES = [
    {'entity': 'China', 'name_zh': '中国', 'name_en': 'China', 'iso': 'cn', 'adif': '318', 'cq': '24', 'itu': '44', 'continent': 'AS',
     'prefixes': ['B','BA','BB','BC','BD','BE','BF','BG','BH','BI','BJ','BL']},
    {'entity': 'Hong Kong', 'name_zh': '中国香港', 'name_en': 'Hong Kong', 'iso': 'hk', 'adif': '321', 'cq': '24', 'itu': '44', 'continent': 'AS',
     'prefixes': ['VR2']},
    {'entity': 'Macau', 'name_zh': '中国澳门', 'name_en': 'Macau', 'iso': 'mo', 'adif': '152', 'cq': '24', 'itu': '44', 'continent': 'AS',
     'prefixes': ['XX9']},
    {'entity': 'Taiwan', 'name_zh': '中国台湾', 'name_en': 'Taiwan', 'iso': 'tw', 'adif': '386', 'cq': '24', 'itu': '44', 'continent': 'AS',
     'prefixes': ['BM','BN','BO','BP','BQ','BU','BV','BW','BX']},
    {'entity': 'Japan', 'name_zh': '日本', 'name_en': 'Japan', 'iso': 'jp', 'adif': '339', 'cq': '25', 'itu': '45', 'continent': 'AS',
     'prefixes': ['7J','7K','7L','7M','7N','8J','8K','8L','8M','8N','JA','JB','JC','JD','JE','JF','JG','JH','JI','JJ','JK','JL','JM','JN','JO','JP','JQ','JR','JS']},
    {'entity': 'South Korea', 'name_zh': '韩国', 'name_en': 'South Korea', 'iso': 'kr', 'adif': '137', 'cq': '25', 'itu': '44', 'continent': 'AS',
     'prefixes': ['6K','6L','6M','DS','DT','HL']},
    {'entity': 'United States', 'name_zh': '美国', 'name_en': 'United States', 'iso': 'us', 'adif': '291', 'cq': '5', 'itu': '8', 'continent': 'NA',
     'prefixes': ['AA','AB','AC','AD','AE','AF','AG','AI','AJ','AK','K','N','W']},
    {'entity': 'Canada', 'name_zh': '加拿大', 'name_en': 'Canada', 'iso': 'ca', 'adif': '1', 'cq': '4', 'itu': '9', 'continent': 'NA',
     'prefixes': ['CF','CG','CH','CI','CJ','CK','VA','VB','VC','VD','VE','VF','VG','VO','VX','VY','XJ','XK','XL','XM','XN','XO']},
    {'entity': 'Australia', 'name_zh': '澳大利亚', 'name_en': 'Australia', 'iso': 'au', 'adif': '150', 'cq': '30', 'itu': '55', 'continent': 'OC',
     'prefixes': ['AX','VH','VI','VK','VL','VM','VN','VZ']},
    {'entity': 'New Zealand', 'name_zh': '新西兰', 'name_en': 'New Zealand', 'iso': 'nz', 'adif': '170', 'cq': '32', 'itu': '60', 'continent': 'OC',
     'prefixes': ['ZK','ZL','ZM']},
    {'entity': 'England', 'name_zh': '英格兰', 'name_en': 'England', 'iso': 'gb', 'adif': '223', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['2E','G','M']},
    {'entity': 'Scotland', 'name_zh': '苏格兰', 'name_en': 'Scotland', 'iso': 'gb', 'adif': '279', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['2M','GM','GS']},
    {'entity': 'Wales', 'name_zh': '威尔士', 'name_en': 'Wales', 'iso': 'gb', 'adif': '294', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['2W','GW','GC']},
    {'entity': 'Northern Ireland', 'name_zh': '北爱尔兰', 'name_en': 'Northern Ireland', 'iso': 'gb', 'adif': '265', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['2I','GI','GN']},
    {'entity': 'France', 'name_zh': '法国', 'name_en': 'France', 'iso': 'fr', 'adif': '227', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['F','HW','HX','HY','TH','TK','TM','TO']},
    {'entity': 'Germany', 'name_zh': '德国', 'name_en': 'Germany', 'iso': 'de', 'adif': '230', 'cq': '14', 'itu': '28', 'continent': 'EU',
     'prefixes': ['DA','DB','DC','DD','DE','DF','DG','DH','DJ','DK','DL','DM','DN','DO','DP','DQ','DR','Y2','Y3','Y4','Y5','Y6','Y7','Y8','Y9']},
    {'entity': 'Spain', 'name_zh': '西班牙', 'name_en': 'Spain', 'iso': 'es', 'adif': '281', 'cq': '14', 'itu': '37', 'continent': 'EU',
     'prefixes': ['AM','AN','AO','EA','EB','EC','ED','EE','EF','EG','EH']},
    {'entity': 'Italy', 'name_zh': '意大利', 'name_en': 'Italy', 'iso': 'it', 'adif': '248', 'cq': '15', 'itu': '28', 'continent': 'EU',
     'prefixes': ['I','IA','IB','IC','ID','IE','IF','IG','IH','II','IJ','IK','IL','IM','IN','IO','IP','IQ','IR','IS','IT','IU','IV','IW','IZ']},
    {'entity': 'Netherlands', 'name_zh': '荷兰', 'name_en': 'Netherlands', 'iso': 'nl', 'adif': '263', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['PA','PB','PC','PD','PE','PF','PG','PH','PI']},
    {'entity': 'Belgium', 'name_zh': '比利时', 'name_en': 'Belgium', 'iso': 'zz', 'adif': '209', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['ON','OO','OP','OR','OS','OT']},
    {'entity': 'Switzerland', 'name_zh': '瑞士', 'name_en': 'Switzerland', 'iso': 'zz', 'adif': '287', 'cq': '14', 'itu': '28', 'continent': 'EU',
     'prefixes': ['HB']},
    {'entity': 'Austria', 'name_zh': '奥地利', 'name_en': 'Austria', 'iso': 'zz', 'adif': '206', 'cq': '15', 'itu': '28', 'continent': 'EU',
     'prefixes': ['OE']},
    {'entity': 'Poland', 'name_zh': '波兰', 'name_en': 'Poland', 'iso': 'zz', 'adif': '269', 'cq': '15', 'itu': '28', 'continent': 'EU',
     'prefixes': ['HF','SN','SO','SP','SQ','SR','3Z']},
    {'entity': 'Czech Republic', 'name_zh': '捷克', 'name_en': 'Czech Republic', 'iso': 'zz', 'adif': '503', 'cq': '15', 'itu': '28', 'continent': 'EU',
     'prefixes': ['OK','OL']},
    {'entity': 'Slovakia', 'name_zh': '斯洛伐克', 'name_en': 'Slovakia', 'iso': 'zz', 'adif': '504', 'cq': '15', 'itu': '28', 'continent': 'EU',
     'prefixes': ['OM']},
    {'entity': 'Denmark', 'name_zh': '丹麦', 'name_en': 'Denmark', 'iso': 'zz', 'adif': '221', 'cq': '14', 'itu': '18', 'continent': 'EU',
     'prefixes': ['5P','5Q','OU','OV','OZ']},
    {'entity': 'Sweden', 'name_zh': '瑞典', 'name_en': 'Sweden', 'iso': 'zz', 'adif': '284', 'cq': '14', 'itu': '18', 'continent': 'EU',
     'prefixes': ['7S','8S','SA','SB','SC','SD','SE','SF','SG','SH','SI','SJ','SK','SL','SM']},
    {'entity': 'Norway', 'name_zh': '挪威', 'name_en': 'Norway', 'iso': 'zz', 'adif': '266', 'cq': '14', 'itu': '18', 'continent': 'EU',
     'prefixes': ['JW','JX','LA','LB','LC','LD','LE','LF','LG','LH','LI','LJ','LK','LM','LN']},
    {'entity': 'Finland', 'name_zh': '芬兰', 'name_en': 'Finland', 'iso': 'zz', 'adif': '224', 'cq': '15', 'itu': '18', 'continent': 'EU',
     'prefixes': ['OF','OG','OH','OI','OJ']},
    {'entity': 'Portugal', 'name_zh': '葡萄牙', 'name_en': 'Portugal', 'iso': 'zz', 'adif': '272', 'cq': '14', 'itu': '37', 'continent': 'EU',
     'prefixes': ['CR','CS','CT']},
    {'entity': 'Ireland', 'name_zh': '爱尔兰', 'name_en': 'Ireland', 'iso': 'zz', 'adif': '245', 'cq': '14', 'itu': '27', 'continent': 'EU',
     'prefixes': ['EI','EJ']},
    {'entity': 'Greece', 'name_zh': '希腊', 'name_en': 'Greece', 'iso': 'zz', 'adif': '236', 'cq': '20', 'itu': '28', 'continent': 'EU',
     'prefixes': ['J4','SV','SX','SY','SZ']},
    {'entity': 'Turkey', 'name_zh': '土耳其', 'name_en': 'Turkey', 'iso': 'zz', 'adif': '390', 'cq': '20', 'itu': '39', 'continent': 'AS',
     'prefixes': ['TA','TB','TC','YM']},
    {'entity': 'European Russia', 'name_zh': '俄罗斯（欧洲部分）', 'name_en': 'European Russia', 'iso': 'ru', 'adif': '54', 'cq': '16', 'itu': '29', 'continent': 'EU',
     'prefixes': ['R1','R2','R3','R4','R6','R7','RA1','RA2','RA3','RA4','RA6','RA7','RC1','RC2','RC3','RC4','RC6','RC7','RD1','RD2','RD3','RD4','RD6','RD7','RE1','RE3','RE4','RE6','RE7','RF1','RF2','RF3','RF4','RF6','RF7','RG1','RG2','RG3','RG4','RG6','RG7','RI1','RI2','RI3','RI4','RI6','RI7','RJ1','RJ2','RJ3','RJ4','RJ6','RJ7','RK1','RK2','RK3','RK4','RK6','RK7','RL1','RL2','RL3','RL4','RL6','RL7','RM1','RM2','RM3','RM4','RM6','RM7','RN1','RN2','RN3','RN4','RN6','RN7','RO1','RO2','RO3','RO4','RO6','RO7','RQ1','RQ2','RQ3','RQ4','RQ6','RQ7','RT1','RT2','RT3','RT4','RT6','RT7','RU1','RU2','RU3','RU4','RU6','RU7','RV1','RV2','RV3','RV4','RV6','RV7','RW1','RW2','RW3','RW4','RW6','RW7','RX1','RX2','RX3','RX4','RX6','RX7','RY1','RY2','RY3','RY4','RY6','RY7','RZ1','RZ2','RZ3','RZ4','RZ6','RZ7','UA1','UA2','UA3','UA4','UA6','UA7','UB1','UB2','UB3','UB4','UB6','UB7','UC1','UC2','UC3','UC4','UC6','UC7','UD1','UD2','UD3','UD4','UD6','UD7','UE1','UE2','UE3','UE4','UE6','UE7','UF1','UF2','UF3','UF4','UF6','UF7','UG1','UG2','UG3','UG4','UG6','UG7','UH1','UH2','UH3','UH4','UH6','UH7','UI1','UI2','UI3','UI4','UI6','UI7']},
    {'entity': 'Asiatic Russia', 'name_zh': '俄罗斯（亚洲部分）', 'name_en': 'Asiatic Russia', 'iso': 'ru', 'adif': '15', 'cq': '17', 'itu': '30', 'continent': 'AS',
     'prefixes': ['R0','R8','R9','RA0','RA8','RA9','RC0','RC8','RC9','RD0','RD8','RD9','RE0','RE8','RE9','RF0','RF8','RF9','RG0','RG8','RG9','RI0','RI8','RI9','RJ0','RJ8','RJ9','RK0','RK8','RK9','RL0','RL8','RL9','RM0','RM8','RM9','RN0','RN8','RN9','RO0','RO8','RO9','RQ0','RQ8','RQ9','RT0','RT8','RT9','RU0','RU8','RU9','RV0','RV8','RV9','RW0','RW8','RW9','RX0','RX8','RX9','RY0','RY8','RY9','RZ0','RZ8','RZ9','UA0','UA8','UA9','UB0','UB8','UB9','UC0','UC8','UC9','UD0','UD8','UD9','UE0','UE8','UE9','UF0','UF8','UF9','UG0','UG8','UG9','UH0','UH8','UH9','UI0','UI8','UI9']},
    {'entity': 'Brazil', 'name_zh': '巴西', 'name_en': 'Brazil', 'iso': 'br', 'adif': '108', 'cq': '11', 'itu': '15', 'continent': 'SA',
     'prefixes': ['PP','PQ','PR','PS','PT','PU','PV','PW','PX','PY','ZV','ZW','ZX','ZY']},
    {'entity': 'Argentina', 'name_zh': '阿根廷', 'name_en': 'Argentina', 'iso': 'ar', 'adif': '100', 'cq': '13', 'itu': '14', 'continent': 'SA',
     'prefixes': ['AY','AZ','LO','LP','LQ','LR','LS','LT','LU','LV','LW']},
    {'entity': 'South Africa', 'name_zh': '南非', 'name_en': 'South Africa', 'iso': 'za', 'adif': '462', 'cq': '38', 'itu': '57', 'continent': 'AF',
     'prefixes': ['ZR','ZS','ZT','ZU']},
    {'entity': 'India', 'name_zh': '印度', 'name_en': 'India', 'iso': 'in', 'adif': '324', 'cq': '22', 'itu': '41', 'continent': 'AS',
     'prefixes': ['AT','AU','VT','VU','VW']},
    {'entity': 'West Malaysia', 'name_zh': '西马来西亚', 'name_en': 'West Malaysia', 'iso': 'my', 'adif': '299', 'cq': '28', 'itu': '54', 'continent': 'AS',
     'prefixes': ['9M2','9W2']},
    {'entity': 'East Malaysia', 'name_zh': '东马来西亚', 'name_en': 'East Malaysia', 'iso': 'my', 'adif': '46', 'cq': '28', 'itu': '54', 'continent': 'OC',
     'prefixes': ['9M6','9W6']},
    {'entity': 'Philippines', 'name_zh': '菲律宾', 'name_en': 'Philippines', 'iso': 'ph', 'adif': '375', 'cq': '27', 'itu': '50', 'continent': 'OC',
     'prefixes': ['4D','4E','4F','DU','DV','DW','DX','DY','DZ']},
    {'entity': 'Thailand', 'name_zh': '泰国', 'name_en': 'Thailand', 'iso': 'th', 'adif': '387', 'cq': '26', 'itu': '49', 'continent': 'AS',
     'prefixes': ['E2','HS']},
    {'entity': 'Indonesia', 'name_zh': '印度尼西亚', 'name_en': 'Indonesia', 'iso': 'id', 'adif': '327', 'cq': '28', 'itu': '54', 'continent': 'OC',
     'prefixes': ['8A','8B','8C','PO','YB','YC','YD','YE','YF','YG','YH']},
]

DXCC_DEFAULT = {'entity': 'Unknown', 'name_zh': 'N/A', 'name_en': 'N/A', 'iso': 'zz', 'adif': '0', 'cq': '', 'itu': '', 'continent': ''}


def _compile_dxcc_rules() -> list[tuple[str, dict[str, str]]]:
    rules: list[tuple[str, dict[str, str]]] = []
    for entry in DXCC_ENTITIES:
        info = {k: str(v) for k, v in entry.items() if k != 'prefixes'}
        for prefix in entry['prefixes']:
            rules.append((prefix.upper(), info))
    rules.sort(key=lambda item: len(item[0]), reverse=True)
    return rules


DXCC_RULES = _compile_dxcc_rules()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)


db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class QSO(db.Model):
    __tablename__ = 'qso'

    id = db.Column(db.Integer, primary_key=True)
    qso_date = db.Column(db.String(10), nullable=False, index=True)
    qso_time_utc = db.Column(db.String(8), nullable=False, index=True)
    callsign = db.Column(db.String(32), nullable=False, index=True)
    band = db.Column(db.String(16), nullable=True, index=True)
    frequency = db.Column(db.String(32), nullable=True, index=True)
    mode = db.Column(db.String(16), nullable=True, index=True)
    rst_sent = db.Column(db.String(8), nullable=True)
    rst_recv = db.Column(db.String(8), nullable=True)
    my_qth = db.Column(db.String(128), nullable=True)
    their_qth = db.Column(db.String(128), nullable=True, index=True)
    radio = db.Column(db.String(128), nullable=True)
    antenna = db.Column(db.String(128), nullable=True)
    power_w = db.Column(db.String(16), nullable=True)
    via_type = db.Column(db.String(16), nullable=True, index=True)
    satellite_name = db.Column(db.String(64), nullable=True)
    repeater_name = db.Column(db.String(64), nullable=True)
    qsl_status = db.Column(db.String(16), nullable=True, default='none', index=True)
    qsl_sent_date = db.Column(db.String(10), nullable=True)
    qsl_received_date = db.Column(db.String(10), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Attachment(db.Model):
    __tablename__ = 'attachment'

    id = db.Column(db.Integer, primary_key=True)
    qso_id = db.Column(db.Integer, db.ForeignKey('qso.id'), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    file_ext = db.Column(db.String(16), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class AppSetting(db.Model):
    __tablename__ = 'app_setting'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=True)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


@app.before_request
def refresh_session_timeout():
    if current_user.is_authenticated:
        session.permanent = True
        session.modified = True


@app.context_processor
def inject_now():
    return {'now': datetime.now()}


def qso_attachments(qso_id: int) -> list[Attachment]:
    return Attachment.query.filter_by(qso_id=qso_id).order_by(Attachment.uploaded_at.desc()).all()


def get_setting(key: str, default: str = '') -> str:
    item = db.session.get(AppSetting, key)
    return item.value if item and item.value is not None else default


def set_setting(key: str, value: str) -> None:
    item = db.session.get(AppSetting, key)
    if item:
        item.value = value
    else:
        db.session.add(AppSetting(key=key, value=value))


def background_image_url() -> str:
    source = get_setting('background_source', 'bing')
    if source == 'upload':
        filename = get_setting('custom_background_file', '')
        if filename:
            return url_for('site_background_file', filename=filename)
    return ''


@app.context_processor
def inject_helpers():
    return {
        'get_qso_attachments': qso_attachments,
        'site_settings': {
            'background_source': get_setting('background_source', 'bing'),
            'admin_bg_opacity': get_setting('admin_bg_opacity', '72'),
            'public_bg_opacity': get_setting('public_bg_opacity', '58'),
            'custom_background_file': get_setting('custom_background_file', ''),
            'solid_background_color': get_setting('solid_background_color', '#0f172a'),
            'interface_language': get_setting('interface_language', 'zh'),
            'theme_preference': get_setting('theme_preference', 'auto'),
        },
        'custom_background_url': background_image_url(),
        'band_options': BAND_OPTIONS,
        'mode_options': MODE_OPTIONS,
        'current_language': current_language(),
        'dxcc_map_json': json.dumps({prefix: {'iso': info.get('iso', 'zz'), 'name': (info['name_en'] if current_language() == 'en' else info['name_zh']), 'adif': info.get('adif', '0'), 'cq': info.get('cq', ''), 'itu': info.get('itu', ''), 'continent': info.get('continent', '')} for prefix, info in DXCC_RULES}, ensure_ascii=False),
    }


@app.template_filter('na')
def na_filter(value):
    value = (value or '').strip() if isinstance(value, str) else value
    return value if value not in (None, '', 'none', 'None') else 'N/A'


@app.template_global()
def yes_no(value):
    return t('yes') if value else t('no')


@app.template_global()
def qsl_sent_flag(qso: QSO) -> bool:
    return bool((qso.qsl_sent_date or '').strip() or (qso.qsl_status or '').strip() in {'sent', 'received', 'both'})


@app.template_global()
def qsl_received_flag(qso: QSO) -> bool:
    return bool((qso.qsl_received_date or '').strip() or (qso.qsl_status or '').strip() in {'received', 'both'})


@app.template_global()
def station_callsign_value() -> str:
    return current_station_callsign()


@app.template_global()
def qso_country_name(qso: QSO) -> str:
    return qso_country(qso)


def fetch_bing_wallpaper(market: str = 'zh-CN') -> dict[str, str]:
    now_ts = datetime.utcnow().timestamp()
    cached = BING_CACHE.get('payload')
    if cached and BING_CACHE.get('expires', 0) > now_ts:
        return cached

    api_url = f'https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt={market}'
    with urlopen(api_url, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8', errors='ignore'))

    images = data.get('images') or []
    if not images:
        raise ValueError('No Bing wallpaper returned')

    item = images[0]
    image_url = item.get('url')
    if image_url and image_url.startswith('/'):
        image_url = f'https://www.bing.com{image_url}'
    payload = {
        'image_url': image_url or '',
        'title': item.get('title') or item.get('headline') or 'Bing Wallpaper',
        'copyright': item.get('copyright') or '',
        'market': market,
    }
    BING_CACHE['payload'] = payload
    BING_CACHE['expires'] = now_ts + 3600
    return payload


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_image(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS


def sanitize_callsign(value: str) -> str:
    return value.strip().upper()


def current_station_callsign() -> str:
    if current_user.is_authenticated:
        return (current_user.username or '').upper()
    first = User.query.order_by(User.id.asc()).first()
    return (first.username or 'N/A').upper() if first else 'N/A'


def current_language() -> str:
    lang = get_setting('interface_language', 'zh').strip().lower()
    return lang if lang in {'zh', 'en'} else 'zh'


def t(key: str) -> str:
    lang = current_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS['zh']).get(key, TRANSLATIONS['zh'].get(key, key))


@app.template_global()
def tr(key: str) -> str:
    return t(key)


def normalize_callsign_for_dxcc(value: str) -> str:
    cs = (value or '').upper().strip()
    cs = re.sub(r'\s+', '', cs)
    if not cs:
        return ''
    parts = [p for p in cs.split('/') if p]
    if len(parts) == 1:
        return parts[0]

    def looks_like_prefix(part: str) -> bool:
        return 1 <= len(part) <= 4 and any(ch.isalpha() for ch in part) and any(ch.isdigit() for ch in part)

    candidates: list[str] = []
    if looks_like_prefix(parts[0]):
        candidates.append(parts[0])
    for part in parts:
        if any(ch.isalpha() for ch in part) and any(ch.isdigit() for ch in part):
            candidates.append(part)
    candidates.extend(parts)

    seen = set()
    ordered: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered[0] if ordered else cs


def qso_dxcc_info_from_callsign(callsign: str) -> dict[str, str]:
    cs = normalize_callsign_for_dxcc(callsign)
    lang = current_language()
    for prefix, info in DXCC_RULES:
        if cs.startswith(prefix):
            result = dict(info)
            result['iso'] = (result.get('iso') or 'zz').lower()
            result['name'] = result['name_en'] if lang == 'en' else result['name_zh']
            return result
    return {
        'entity': DXCC_DEFAULT['entity'],
        'iso': 'zz',
        'adif': DXCC_DEFAULT['adif'],
        'cq': DXCC_DEFAULT['cq'],
        'itu': DXCC_DEFAULT['itu'],
        'continent': DXCC_DEFAULT['continent'],
        'name': DXCC_DEFAULT['name_en'] if lang == 'en' else DXCC_DEFAULT['name_zh'],
        'name_zh': DXCC_DEFAULT['name_zh'],
        'name_en': DXCC_DEFAULT['name_en'],
    }


def qso_country(qso: QSO) -> str:
    return qso_dxcc_info_from_callsign((qso.callsign or '')).get('name', 'N/A')


@app.template_global()
def qso_dxcc_iso(qso: QSO) -> str:
    return qso_dxcc_info_from_callsign((qso.callsign or '')).get('iso', 'zz')


@app.template_global()
def qso_dxcc_name(qso: QSO) -> str:
    return qso_dxcc_info_from_callsign((qso.callsign or '')).get('name', 'N/A')


@app.template_global()
def qso_dxcc_adif(qso: QSO) -> str:
    return qso_dxcc_info_from_callsign((qso.callsign or '')).get('adif', '0')


@app.template_global()
def qso_dxcc_cq(qso: QSO) -> str:
    return qso_dxcc_info_from_callsign((qso.callsign or '')).get('cq', '')


@app.template_global()
def qso_dxcc_itu(qso: QSO) -> str:
    return qso_dxcc_info_from_callsign((qso.callsign or '')).get('itu', '')


def normalize_utc_time(value: str) -> str:
    value = (value or '').strip()
    digits = ''.join(ch for ch in value if ch.isdigit())
    if len(digits) >= 6:
        return f'{digits[0:2]}:{digits[2:4]}:{digits[4:6]}'
    if len(digits) >= 4:
        return f'{digits[0:2]}:{digits[2:4]}'
    return value


def normalize_qso_date(value: str) -> str:
    value = (value or '').strip()
    digits = ''.join(ch for ch in value if ch.isdigit())
    if len(digits) == 8:
        return f'{digits[0:4]}-{digits[4:6]}-{digits[6:8]}'
    return value


def table_columns(table_name: str) -> set[str]:
    rows = db.session.execute(text(f'PRAGMA table_info({table_name})')).all()
    return {row[1] for row in rows}


def migrate_schema() -> None:
    db.create_all()
    qso_cols = table_columns('qso') if db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='qso'")).first() else set()
    needed = {
        'qsl_status': "ALTER TABLE qso ADD COLUMN qsl_status VARCHAR(16)",
        'qsl_sent_date': "ALTER TABLE qso ADD COLUMN qsl_sent_date VARCHAR(10)",
        'qsl_received_date': "ALTER TABLE qso ADD COLUMN qsl_received_date VARCHAR(10)",
    }
    changed = False
    for col, sql in needed.items():
        if col not in qso_cols:
            db.session.execute(text(sql))
            changed = True
    if changed:
        db.session.commit()


def seed_admin() -> None:
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()


def seed_demo_qso() -> None:
    if QSO.query.count() == 0:
        sample = QSO(
            qso_date='2026-04-08',
            qso_time_utc='03:33',
            callsign='BI8SCC',
            band='2m',
            frequency='145.825',
            mode='FM',
            rst_sent='59',
            rst_recv='59',
            my_qth='Wuhan, Hubei',
            their_qth='Taiyuan, Shanxi',
            radio='VR-N76',
            antenna='5-element Yagi',
            power_w='5',
            via_type='satellite',
            satellite_name='ISS',
            qsl_status='pending',
            notes='Demo record for prototype.',
        )
        db.session.add(sample)
        db.session.commit()


def seed_settings() -> None:
    defaults = {
        'background_source': 'bing',
        'admin_bg_opacity': '72',
        'public_bg_opacity': '58',
        'custom_background_file': '',
        'solid_background_color': '#0f172a',
        'interface_language': 'zh',
        'theme_preference': 'auto',
    }
    changed = False
    for key, value in defaults.items():
        if db.session.get(AppSetting, key) is None:
            db.session.add(AppSetting(key=key, value=value))
            changed = True
    if changed:
        db.session.commit()


def qso_from_form(qso: QSO) -> QSO:
    qso.qso_date = normalize_qso_date(request.form.get('qso_date', ''))
    qso.qso_time_utc = normalize_utc_time(request.form.get('qso_time_utc', ''))
    qso.callsign = sanitize_callsign(request.form.get('callsign', ''))
    qso.band = request.form.get('band', '').strip()
    qso.frequency = request.form.get('frequency', '').strip()
    qso.mode = request.form.get('mode', '').strip().upper()
    qso.rst_sent = request.form.get('rst_sent', '').strip()
    qso.rst_recv = request.form.get('rst_recv', '').strip()
    qso.my_qth = ''
    qso.their_qth = request.form.get('their_qth', '').strip()
    qso.radio = request.form.get('radio', '').strip()
    qso.antenna = request.form.get('antenna', '').strip()
    qso.power_w = request.form.get('power_w', '').strip()
    qso.via_type = ''
    qso.satellite_name = ''
    qso.repeater_name = ''
    qsl_sent = request.form.get('qsl_sent', 'no').strip().lower()
    qsl_received = request.form.get('qsl_received', 'no').strip().lower()
    qso.qsl_sent_date = request.form.get('qsl_sent_date', '').strip() if qsl_sent == 'yes' else ''
    qso.qsl_received_date = request.form.get('qsl_received_date', '').strip() if qsl_received == 'yes' else ''
    if qsl_received == 'yes':
        qso.qsl_status = 'received'
    elif qsl_sent == 'yes':
        qso.qsl_status = 'sent'
    else:
        qso.qsl_status = ''
    qso.notes = request.form.get('notes', '').strip()
    return qso


def validate_qso(qso: QSO) -> str | None:
    if not qso.qso_date or not qso.qso_time_utc or not qso.callsign:
        return '日期、UTC时间、呼号为必填项'
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', qso.qso_date or ''):
        return 'QSO 日期格式应为 YYYY-MM-DD'
    if not re.fullmatch(r'\d{2}:\d{2}(:\d{2})?', qso.qso_time_utc or ''):
        return 'UTC 时间格式应为 HH:MM 或 HH:MM:SS'
    return None


def save_uploaded_files(qso_id: int, files: Iterable) -> int:
    count = 0
    for file in files:
        if not file or not file.filename:
            continue
        if not allowed_file(file.filename):
            flash(f'文件 {file.filename} 类型不支持', 'danger')
            continue
        original_name = file.filename
        safe_name = secure_filename(original_name)
        ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else ''
        stamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        stored_name = f'{qso_id}_{stamp}_{safe_name}'
        file.save(UPLOAD_DIR / stored_name)
        db.session.add(Attachment(
            qso_id=qso_id,
            original_name=original_name,
            stored_name=stored_name,
            file_ext=ext,
        ))
        count += 1
    if count:
        db.session.commit()
    return count


def save_custom_background(file) -> str:
    if not file or not file.filename:
        raise ValueError('请选择背景图片')
    if not allowed_image(file.filename):
        raise ValueError('仅支持 png/jpg/jpeg/gif/webp 背景图')
    safe_name = secure_filename(file.filename)
    ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else 'jpg'
    filename = f'custom_bg_{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}.{ext}'
    for old in BACKGROUND_DIR.iterdir():
        if old.is_file() and old.name.startswith('custom_bg_'):
            old.unlink(missing_ok=True)
    file.save(BACKGROUND_DIR / filename)
    set_setting('custom_background_file', filename)
    set_setting('background_source', 'upload')
    db.session.commit()
    return filename


def parse_adif_date(value: str) -> str:
    value = (value or '').strip()
    if len(value) == 8 and value.isdigit():
        return f'{value[0:4]}-{value[4:6]}-{value[6:8]}'
    return value


def parse_adif_time(value: str) -> str:
    value = (value or '').strip()
    digits = ''.join(ch for ch in value if ch.isdigit())
    if len(digits) >= 6:
        return f'{digits[0:2]}:{digits[2:4]}:{digits[4:6]}'
    if len(digits) >= 4:
        return f'{digits[0:2]}:{digits[2:4]}'
    return value


def parse_adif_records(content: str) -> list[dict[str, str]]:
    body = re.sub(r'(?is)^.*?<eoh>', '', content)
    chunks = re.split(r'(?i)<eor>', body)
    records: list[dict[str, str]] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        pos = 0
        record: dict[str, str] = {}
        while True:
            m = re.search(r'<([^:>]+):(\d+)(:[^>]+)?>', chunk[pos:], re.I)
            if not m:
                break
            end = pos + m.end()
            field = m.group(1).lower()
            length = int(m.group(2))
            value = chunk[end:end + length]
            record[field] = value.strip()
            pos = end + length
        if record:
            records.append(record)
    return records


def qso_from_adif(record: dict[str, str]) -> QSO:
    via = record.get('prop_mode', '') or record.get('submode', '')
    via = via.lower()
    return QSO(
        qso_date=parse_adif_date(record.get('qso_date', '')) or datetime.utcnow().strftime('%Y-%m-%d'),
        qso_time_utc=parse_adif_time(record.get('time_on', '')) or '00:00:00',
        callsign=sanitize_callsign(record.get('call', 'UNKNOWN')),
        band=record.get('band', ''),
        frequency=record.get('freq', ''),
        mode=(record.get('mode', '') or '').upper(),
        rst_sent=record.get('rst_sent', ''),
        rst_recv=record.get('rst_rcvd', ''),
        my_qth=record.get('my_city', '') or record.get('station_callsign', ''),
        their_qth=record.get('qth', '') or record.get('city', ''),
        power_w=record.get('tx_pwr', ''),
        via_type=via if via in {'simplex', 'repeater', 'satellite', 'aprs', 'hotspot', 'hf_direct'} else '',
        satellite_name=record.get('sat_name', ''),
        repeater_name=record.get('comment', '') if 'repeater' in via else '',
        qsl_status='none',
        notes=record.get('comment', ''),
    )


def qso_to_adif(qso: QSO) -> str:
    def fmt(name: str, value: str) -> str:
        value = value or ''
        return f'<{name}:{len(value)}>{value}' if value else ''

    date_compact = (qso.qso_date or '').replace('-', '')
    digits = ''.join(ch for ch in (qso.qso_time_utc or '') if ch.isdigit())
    time_compact = digits if len(digits) >= 6 else (digits + '00' if len(digits) == 4 else digits)
    parts = [
        fmt('QSO_DATE', date_compact),
        fmt('TIME_ON', time_compact),
        fmt('CALL', qso.callsign),
        fmt('BAND', qso.band or ''),
        fmt('FREQ', qso.frequency or ''),
        fmt('MODE', qso.mode or ''),
        fmt('RST_SENT', qso.rst_sent or ''),
        fmt('RST_RCVD', qso.rst_recv or ''),
        fmt('QTH', qso.their_qth or ''),
        fmt('TX_PWR', qso.power_w or ''),
        fmt('SAT_NAME', qso.satellite_name or ''),
        fmt('DXCC', qso_dxcc_info_from_callsign(qso.callsign).get('adif', '0')),
        fmt('CQZ', qso_dxcc_info_from_callsign(qso.callsign).get('cq', '')),
        fmt('ITUZ', qso_dxcc_info_from_callsign(qso.callsign).get('itu', '')),
        fmt('COMMENT', qso.notes or ''),
    ]
    return ''.join(part for part in parts if part) + '<EOR>\n'


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('public_qso_list'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session.permanent = True
            flash('登录成功', 'success')
            return redirect(url_for('dashboard'))
        flash('用户名或密码错误', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('public_qso_list'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    user = db.session.get(User, current_user.id)
    if request.method == 'POST':
        action = request.form.get('action', '').strip()
        if action == 'username':
            new_username = request.form.get('new_username', '').strip().upper()
            if not new_username:
                flash('用户名不能为空', 'danger')
            elif len(new_username) < 3:
                flash('用户名至少 3 位', 'danger')
            elif len(new_username) > 64:
                flash('用户名不能超过 64 位', 'danger')
            else:
                exists = User.query.filter(User.username == new_username, User.id != current_user.id).first()
                if exists:
                    flash('该用户名已存在', 'danger')
                else:
                    user.username = new_username
                    db.session.commit()
                    flash('用户名已更新', 'success')
        elif action == 'password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            if not user or not user.check_password(current_password):
                flash('当前密码不正确', 'danger')
            elif len(new_password) < 6:
                flash('新密码至少 6 位', 'danger')
            elif new_password != confirm_password:
                flash('两次输入的新密码不一致', 'danger')
            else:
                user.set_password(new_password)
                db.session.commit()
                flash('密码已更新', 'success')
        elif action == 'save_opacity':
            admin_opacity = request.form.get('admin_bg_opacity', '72').strip()
            public_opacity = request.form.get('public_bg_opacity', '58').strip()
            try:
                a = max(0, min(100, int(admin_opacity)))
                p = max(0, min(100, int(public_opacity)))
            except ValueError:
                flash('透明度必须是 0 到 100 的整数', 'danger')
                return redirect(url_for('settings_page'))
            set_setting('admin_bg_opacity', str(a))
            set_setting('public_bg_opacity', str(p))
            db.session.commit()
            flash('背景透明度已更新', 'success')
        elif action == 'save_source':
            source = request.form.get('background_source', 'bing').strip()
            if source not in {'bing', 'upload', 'gradient', 'solid'}:
                flash('背景来源无效', 'danger')
            elif source == 'upload' and not get_setting('custom_background_file', ''):
                flash('请先上传背景图，再切换到自定义背景', 'danger')
            else:
                set_setting('background_source', source)
                db.session.commit()
                flash('背景来源已更新', 'success')
        elif action == 'upload_background':
            file = request.files.get('background_file')
            try:
                save_custom_background(file)
                flash('背景图已上传，并已切换为自定义背景', 'success')
            except ValueError as exc:
                flash(str(exc), 'danger')
        elif action == 'save_solid_color':
            color = request.form.get('solid_background_color', '#0f172a').strip()
            if not re.fullmatch(r'#[0-9A-Fa-f]{6}', color):
                flash('纯色背景颜色格式无效', 'danger')
            else:
                set_setting('solid_background_color', color)
                db.session.commit()
                flash('纯色背景颜色已更新', 'success')
        elif action == 'save_theme':
            theme = request.form.get('theme_preference', 'auto').strip().lower()
            if theme not in {'auto', 'light', 'dark'}:
                flash('主题模式无效', 'danger')
            else:
                set_setting('theme_preference', theme)
                db.session.commit()
                flash('主题模式已更新', 'success')
        elif action == 'save_language':
            lang = request.form.get('interface_language', 'zh').strip().lower()
            if lang not in {'zh', 'en'}:
                flash('界面语言无效', 'danger')
            else:
                set_setting('interface_language', lang)
                db.session.commit()
                flash('界面语言已更新', 'success')
        return redirect(url_for('settings_page'))
    return render_template('settings.html')


@app.route('/settings/password')
@login_required
def change_password():
    return redirect(url_for('settings_page'))


@app.route('/settings/appearance')
@login_required
def appearance_settings():
    return redirect(url_for('settings_page'))


@app.route('/about')
@login_required
def about_page():
    return render_template('about.html')


@app.route('/dashboard')
@login_required
def dashboard():
    total_qsos = QSO.query.count()
    qsos = QSO.query.order_by(QSO.qso_date.desc(), QSO.qso_time_utc.desc()).all()
    modes = db.session.query(QSO.mode, db.func.count(QSO.id)).group_by(QSO.mode).order_by(db.func.count(QSO.id).desc()).all()
    return render_template(
        'dashboard.html',
        total_qsos=total_qsos,
        qsos=qsos,
        modes=modes,
    )


@app.route('/qsos')
@login_required
def qso_list():
    query = QSO.query
    callsign = request.args.get('callsign', '').strip()
    mode = request.args.get('mode', '').strip()
    band = request.args.get('band', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    frequency = request.args.get('frequency', '').strip()

    if callsign:
        query = query.filter(QSO.callsign.ilike(f'%{callsign}%'))
    if mode:
        query = query.filter(QSO.mode == mode)
    if band:
        query = query.filter(QSO.band == band)
    if frequency:
        query = query.filter(QSO.frequency.ilike(f'%{frequency}%'))
    if date_from:
        query = query.filter(QSO.qso_date >= date_from)
    if date_to:
        query = query.filter(QSO.qso_date <= date_to)

    qsos = query.order_by(QSO.qso_date.desc(), QSO.qso_time_utc.desc()).all()
    return render_template('qso_list.html', qsos=qsos)


@app.route('/qsos/new', methods=['GET', 'POST'])
@login_required
def qso_create():
    qso = QSO(qsl_status='')
    if request.method == 'POST':
        qso = qso_from_form(qso)
        error = validate_qso(qso)
        if error:
            flash(error, 'danger')
            return render_template('qso_form.html', qso=qso, form_title='新增 QSO')
        db.session.add(qso)
        db.session.commit()
        uploaded = save_uploaded_files(qso.id, request.files.getlist('attachments'))
        if uploaded:
            flash(f'QSO 已新增，并上传 {uploaded} 个附件', 'success')
        else:
            flash('QSO 已新增', 'success')
        return redirect(url_for('qso_list'))
    return render_template('qso_form.html', qso=qso, form_title='新增 QSO')


@app.route('/qsos/<int:qso_id>')
@login_required
def qso_detail(qso_id: int):
    qso = QSO.query.get_or_404(qso_id)
    attachments = qso_attachments(qso.id)
    return render_template('qso_detail.html', qso=qso, attachments=attachments)


@app.route('/qsos/<int:qso_id>/edit', methods=['GET', 'POST'])
@login_required
def qso_edit(qso_id: int):
    qso = QSO.query.get_or_404(qso_id)
    if request.method == 'POST':
        qso = qso_from_form(qso)
        error = validate_qso(qso)
        if error:
            flash(error, 'danger')
            return render_template('qso_form.html', qso=qso, form_title='编辑 QSO')
        db.session.commit()
        uploaded = save_uploaded_files(qso.id, request.files.getlist('attachments'))
        if uploaded:
            flash(f'QSO 已更新，并新增 {uploaded} 个附件', 'success')
        else:
            flash('QSO 已更新', 'success')
        return redirect(url_for('qso_list'))
    return render_template('qso_form.html', qso=qso, form_title='编辑 QSO')


@app.route('/qsos/<int:qso_id>/delete', methods=['POST'])
@login_required
def qso_delete(qso_id: int):
    qso = QSO.query.get_or_404(qso_id)
    attachments = qso_attachments(qso.id)
    for attachment in attachments:
        try:
            (UPLOAD_DIR / attachment.stored_name).unlink(missing_ok=True)
        except OSError:
            pass
        db.session.delete(attachment)
    db.session.delete(qso)
    db.session.commit()
    flash('QSO 已删除', 'info')
    return redirect(url_for('qso_list'))


@app.route('/attachments/<int:attachment_id>/download')
@login_required
def attachment_download(attachment_id: int):
    attachment = Attachment.query.get_or_404(attachment_id)
    return send_from_directory(UPLOAD_DIR, attachment.stored_name, as_attachment=True, download_name=attachment.original_name)


@app.route('/attachments/<int:attachment_id>/delete', methods=['POST'])
@login_required
def attachment_delete(attachment_id: int):
    attachment = Attachment.query.get_or_404(attachment_id)
    qso_id = attachment.qso_id
    try:
        (UPLOAD_DIR / attachment.stored_name).unlink(missing_ok=True)
    except OSError:
        pass
    db.session.delete(attachment)
    db.session.commit()
    flash('附件已删除', 'info')
    return redirect(url_for('qso_detail', qso_id=qso_id))


@app.route('/adif/export')
@login_required
def adif_export():
    qsos = QSO.query.order_by(QSO.qso_date.asc(), QSO.qso_time_utc.asc()).all()
    header = 'HamLog ADIF Export\n<ADIF_VER:5>3.1.4\n<PROGRAMID:6>HamLog\n<EOH>\n'
    body = ''.join(qso_to_adif(qso) for qso in qsos)
    filename = f'hamlog_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.adi'
    return Response(
        header + body,
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@app.route('/adif/import', methods=['GET', 'POST'])
@login_required
def adif_import():
    imported = 0
    if request.method == 'POST':
        file = request.files.get('adif_file')
        if not file or not file.filename:
            flash('请选择 ADIF 文件', 'danger')
        else:
            content = file.read().decode('utf-8', errors='ignore')
            records = parse_adif_records(content)
            for record in records:
                qso = qso_from_adif(record)
                db.session.add(qso)
                imported += 1
            db.session.commit()
            flash(f'已导入 {imported} 条记录', 'success')
            return redirect(url_for('qso_list'))
    return render_template('adif_import.html')


@app.route('/api/bing-wallpaper')
def bing_wallpaper_api():
    market = request.args.get('mkt', 'zh-CN').strip() or 'zh-CN'
    try:
        return fetch_bing_wallpaper(market)
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {'image_url': '', 'title': '', 'copyright': '', 'market': market}, 200


@app.route('/media/backgrounds/<path:filename>')
def site_background_file(filename: str):
    return send_from_directory(BACKGROUND_DIR, filename)


@app.route('/public')
def public_qso_list():
    query = QSO.query
    callsign = request.args.get('callsign', '').strip()
    mode = request.args.get('mode', '').strip()
    band = request.args.get('band', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    if callsign:
        query = query.filter(QSO.callsign.ilike(f'%{callsign}%'))
    if mode:
        query = query.filter(QSO.mode.ilike(f'%{mode}%'))
    if band:
        query = query.filter(QSO.band == band)
    if date_from:
        query = query.filter(QSO.qso_date >= date_from)
    if date_to:
        query = query.filter(QSO.qso_date <= date_to)
    qsos = query.order_by(QSO.qso_date.desc(), QSO.qso_time_utc.desc()).limit(10).all()
    return render_template('public_qso_list.html', qsos=qsos)


@app.route('/public/qsos/<int:qso_id>')
def public_qso_detail(qso_id: int):
    qso = QSO.query.get_or_404(qso_id)
    return render_template('public_qso_detail.html', qso=qso)


with app.app_context():
    migrate_schema()
    seed_admin()
    seed_demo_qso()
    seed_settings()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

#!/usr/bin/env python3
"""
账号管理器 - 管理多平台发布账号
目前支持：微信公众号
"""

import json
import os
from typing import Dict, List, Optional


class AccountManager:
    """账号 CRUD 操作"""

    def __init__(self, accounts_file: str = None):
        if accounts_file is None:
            accounts_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'accounts.json'
            )
        self.accounts_file = accounts_file
        self._data = None
        self._load()

    def _load(self):
        """加载配置文件"""
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file, encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {"version": 1, "accounts": []}

    def save(self):
        """保存配置文件"""
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ---- 基础查询 ----

    def get_all_accounts(self) -> List[Dict]:
        """返回所有账号列表"""
        return self._data.get('accounts', [])

    def get_account(self, account_id: str) -> Optional[Dict]:
        """根据 ID 获取单个账号"""
        for a in self._data.get('accounts', []):
            if a['id'] == account_id:
                return a
        return None

    def get_accounts_by_platform(self, platform: str) -> List[Dict]:
        """根据平台类型获取账号列表"""
        return [a for a in self.get_all_accounts() if a.get('platform') == platform]

    def get_wechat_accounts(self) -> List[Dict]:
        """获取所有微信公众号账号"""
        return self.get_accounts_by_platform('wechat')

    # ---- CRUD 操作 ----

    def add_account(self, account: Dict) -> bool:
        """添加新账号（ID 唯一性检查）"""
        for a in self._data.get('accounts', []):
            if a['id'] == account['id']:
                return False  # ID 已存在
        self._data.setdefault('accounts', []).append(account)
        self.save()
        return True

    def update_account(self, account_id: str, updates: Dict) -> bool:
        """更新账号配置（部分更新）"""
        for i, a in enumerate(self._data.get('accounts', [])):
            if a['id'] == account_id:
                self._data['accounts'][i].update(updates)
                self.save()
                return True
        return False

    def delete_account(self, account_id: str) -> bool:
        """删除账号"""
        accounts = self._data.get('accounts', [])
        for i, a in enumerate(accounts):
            if a['id'] == account_id:
                del accounts[i]
                self.save()
                return True
        return False

    def test_account(self, account_id: str) -> Dict:
        """测试账号连接状态"""
        account = self.get_account(account_id)
        if not account:
            return {'success': False, 'message': '账号不存在'}

        if account.get('platform') == 'wechat':
            import requests
            try:
                resp = requests.get(
                    "https://api.weixin.qq.com/cgi-bin/token",
                    params={
                        "grant_type": "client_credential",
                        "appid": account.get('app_id', ''),
                        "secret": account.get('app_secret', '')
                    },
                    timeout=10
                )
                data = resp.json()
                if data.get('access_token'):
                    return {
                        'success': True,
                        'message': f"连接成功！token 有效期 {data.get('expires_in', 0)//60} 分钟"
                    }
                else:
                    return {
                        'success': False,
                        'message': f"连接失败: {data.get('errmsg', str(data))}"
                    }
            except Exception as e:
                return {'success': False, 'message': f"连接异常: {e}"}

        return {'success': False, 'message': '不支持的平台类型'}


if __name__ == '__main__':
    # 测试
    am = AccountManager()
    print(f"账号总数: {len(am.get_all_accounts())}")
    print(f"微信公众号: {len(am.get_wechat_accounts())} 个")

#!/usr/bin/env python3
"""
赛道管理器 - 管理内容赛道配置（订阅源、Prompt、发布策略）
"""

import json
import os
from typing import Dict, List, Optional


class TrackManager:
    """赛道 CRUD 操作"""

    def __init__(self, tracks_file: str = None):
        if tracks_file is None:
            tracks_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'tracks.json'
            )
        self.tracks_file = tracks_file
        self._data = None
        self._load()

    def _load(self):
        """加载配置文件"""
        if os.path.exists(self.tracks_file):
            with open(self.tracks_file, encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {"version": 1, "active_track": None, "tracks": []}

    def save(self):
        """保存配置文件"""
        with open(self.tracks_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ---- 基础查询 ----

    def get_all_tracks(self) -> List[Dict]:
        """返回所有赛道列表"""
        return self._data.get('tracks', [])

    def get_track(self, track_id: str) -> Optional[Dict]:
        """根据 ID 获取单个赛道"""
        for t in self._data.get('tracks', []):
            if t['id'] == track_id:
                return t
        return None

    def get_active_track(self) -> Optional[Dict]:
        """获取当前活跃赛道"""
        active = self._data.get('active_track')
        if active:
            return self.get_track(active)
        # fallback: 返回第一个启用的赛道
        for t in self.get_all_tracks():
            if t.get('enabled', True):
                return t
        return None

    def get_enabled_tracks(self) -> List[Dict]:
        """返回所有启用的赛道"""
        return [t for t in self.get_all_tracks() if t.get('enabled', True)]

    def get_active_feeds(self, track_id: str) -> List[Dict]:
        """获取赛道下所有启用的订阅源"""
        track = self.get_track(track_id)
        if not track:
            return []
        return [f for f in track.get('feeds', []) if f.get('enabled', True)]

    def get_track_prompt(self, track_id: str) -> str:
        """获取赛道专属改写 Prompt"""
        track = self.get_track(track_id)
        if track:
            return track.get('rewriter_prompt', '')
        return ''

    def get_track_publish_config(self, track_id: str) -> Dict:
        """获取赛道发布配置"""
        track = self.get_track(track_id)
        if track:
            return track.get('publish', {})
        return {}

    # ---- CRUD 操作 ----

    def add_track(self, track: Dict) -> bool:
        """添加新赛道（ID 唯一性检查）"""
        for t in self._data.get('tracks', []):
            if t['id'] == track['id']:
                return False  # ID 已存在
        self._data.setdefault('tracks', []).append(track)
        self.save()
        return True

    def update_track(self, track_id: str, updates: Dict) -> bool:
        """更新赛道配置（部分更新）"""
        for i, t in enumerate(self._data.get('tracks', [])):
            if t['id'] == track_id:
                self._data['tracks'][i].update(updates)
                self.save()
                return True
        return False

    def delete_track(self, track_id: str) -> bool:
        """删除赛道"""
        tracks = self._data.get('tracks', [])
        for i, t in enumerate(tracks):
            if t['id'] == track_id:
                del tracks[i]
                # 如果删的是活跃赛道，切换到第一个可用
                if self._data.get('active_track') == track_id:
                    enabled = self.get_enabled_tracks()
                    self._data['active_track'] = enabled[0]['id'] if enabled else None
                self.save()
                return True
        return False

    def set_active_track(self, track_id: str) -> bool:
        """设置活跃赛道"""
        if self.get_track(track_id):
            self._data['active_track'] = track_id
            self.save()
            return True
        return False

    # ---- Feed 管理 ----

    def add_feed(self, track_id: str, feed: Dict) -> bool:
        """向赛道添加订阅源"""
        track = self.get_track(track_id)
        if not track:
            return False
        # 检查 URL 唯一性
        for f in track.get('feeds', []):
            if f['url'] == feed['url']:
                return False
        track.setdefault('feeds', []).append(feed)
        self.save()
        return True

    def remove_feed(self, track_id: str, feed_url: str) -> bool:
        """从赛道移除订阅源"""
        track = self.get_track(track_id)
        if not track:
            return False
        feeds = track.get('feeds', [])
        for i, f in enumerate(feeds):
            if f['url'] == feed_url:
                del feeds[i]
                self.save()
                return True
        return False

    def toggle_feed(self, track_id: str, feed_url: str, enabled: bool) -> bool:
        """启用/禁用订阅源"""
        track = self.get_track(track_id)
        if not track:
            return False
        for f in track.get('feeds', []):
            if f['url'] == feed_url:
                f['enabled'] = enabled
                self.save()
                return True
        return False


if __name__ == '__main__':
    # 测试
    tm = TrackManager()
    print('所有赛道:', [t['id'] for t in tm.get_all_tracks()])
    active = tm.get_active_track()
    if active:
        print('活跃赛道:', active['id'])
        print('订阅源:', [f['name'] for f in tm.get_active_feeds(active['id'])])
        print('Prompt 长度:', len(tm.get_track_prompt(active['id'])))

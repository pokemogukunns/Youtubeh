from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class CHZZKLiveIE(InfoExtractor):
    IE_NAME = 'chzzk:live'
    _VALID_URL = r'https?://chzzk\.naver\.com/live/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'https://chzzk.naver.com/live/c68b8ef525fb3d2fa146344d84991753',
        'info_dict': {
            "id": "c68b8ef525fb3d2fa146344d84991753",
            "ext": "mp4",
            'title': str,
            'channel': '진짜도현',
            'channel_id': 'c68b8ef525fb3d2fa146344d84991753',
            'channel_is_verified': False,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1705510344,
            'upload_date': '20240117',
            'live_status': 'is_live',
            'view_count': int,
        },
        'skip': 'The channel is not currently live',
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        live_detail = self._download_json(
            f'https://api.chzzk.naver.com/service/v2/channels/{channel_id}/live-detail', channel_id,
            note='Downloading channel info', errnote='Unable to download channel info')['content']

        if live_detail.get('status') == 'CLOSE':
            raise ExtractorError('The channel is not currently live', expected=True)

        live_playback = self._parse_json(live_detail['livePlaybackJson'], channel_id)

        thumbnails = []
        thumbnail_template = traverse_obj(
            live_playback, ('thumbnail', 'snapshotThumbnailTemplate', {url_or_none}))
        if thumbnail_template:
            for width in traverse_obj(live_playback, ('thumbnail', 'types', ..., {str})):
                thumbnails.append({
                    'id': width,
                    'url': thumbnail_template.replace('{type}', width),
                    'width': int_or_none(width),
                })

        formats, subtitles = [], {}
        for media in traverse_obj(live_playback, ('media', lambda _, v: url_or_none(v['path']))):
            is_low_latency = media.get('mediaId') == 'LLHLS'
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                media['path'], channel_id, 'mp4', fatal=False, live=True,
                m3u8_id='hls-ll' if is_low_latency else 'hls')
            for f in fmts:
                if is_low_latency:
                    f['source_preference'] = -2
                if '-afragalow.stream-audio.stream' in f['format_id']:
                    f['quality'] = -2
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': str(channel_id),
            'title': live_detail.get('liveTitle'),
            'thumbnails': thumbnails,
            **traverse_obj(live_detail, {
                'timestamp': ('openDate', {lambda d: parse_iso8601(d, ' ')}),
                'view_count': ('concurrentUserCount', {int_or_none}),
                'channel': ('channel', 'channelName', {str}),
                'channel_id': ('channel', 'channelId', {str}),
                'channel_is_verified': ('channel', 'verifiedMark', {bool}),
            }),
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles,
        }


class CHZZKVideoIE(InfoExtractor):
    IE_NAME = 'chzzk:video'
    _VALID_URL = r'https?://chzzk\.naver\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://chzzk.naver.com/video/1754',
        "md5": "b0c0c1bb888d913b93d702b1512c7f06",
        'info_dict': {
            "id": "1754",
            "ext": "mp4",
            'title': '치지직 테스트 방송',
            'channel': '침착맨',
            'channel_id': 'bb382c2c0cc9fa7c86ab3b037fb5799c',
            'channel_is_verified': False,
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 15577,
            'timestamp': 1702970505,
            'upload_date': '20231219',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_meta = self._download_json(
            f'https://api.chzzk.naver.com/service/v2/videos/{video_id}', video_id,
            note='Downloading video info', errnote='Unable to download video info')['content']
        vod_id = video_meta.get('videoId')
        in_key = video_meta.get('inKey')
        playback_xml = self._download_xml(
            f'https://apis.naver.com/neonplayer/vodplay/v1/playback/{vod_id}', video_id,
            query={
                'key': in_key,
                'env': 'real',
                'lc': 'en_US',
                'cpl': 'en_US',
            },
            note='Downloading video playback',
            errnote='Unable to download video playback')

        formats, subtitles = self._parse_mpd_formats_and_subtitles(playback_xml)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_meta, {
                'title': ('videoTitle', {str}),
                'thumbnail': ('thumbnailImageUrl', {url_or_none}),
                'timestamp': ('publishDateAt', {lambda t: int_or_none(t / 1000)}),
                'view_count': ('readCount', {int_or_none}),
                'duration': ('duration', {int_or_none}),
                'channel': ('channel', 'channelName', {str}),
                'channel_id': ('channel', 'channelId', {str}),
                'channel_is_verified': ('channel', 'verifiedMark', {bool}),
            }),
        }

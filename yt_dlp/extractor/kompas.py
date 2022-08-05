from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    str_or_none,
    traverse_obj,
)

# Video from www.kompas.tv and video.kompas.com seems use jixie player
# see [1] https://jixie.atlassian.net/servicedesk/customer/portal/2/article/1339654214?src=-1456335525,
# [2] https://scripts.jixie.media/jxvideo.3.1.min.js for more info

class KompasVideoIE(InfoExtractor):
    _VALID_URL = r'https?://video\.kompas\.com/\w+/(?P<id>\d+)/(?P<slug>[\w-]+)'
    _TESTS = [{
        'url': 'https://video.kompas.com/watch/164474/kim-jong-un-siap-kirim-nuklir-lawan-as-dan-korsel',
        'info_dict': {
            'id': '164474',
            'ext': 'mp4',
            'title': 'Kim Jong Un Siap Kirim Nuklir Lawan AS dan Korsel',
            'description': 'md5:262530c4fb7462398235f9a5dba92456',
            'uploader_id': '9262bf2590d558736cac4fff7978fcb1',
            'display_id': 'kim-jong-un-siap-kirim-nuklir-lawan-as-dan-korsel',
            'duration': 85.066667,
            'categories': ['news'],
            'thumbnail': 'https://video.jixie.media/1001/164474/164474_426x240.jpg',
            'tags': ['kcm', 'news', 'korea-utara', 'kim-jong-un', 'senjata-nuklir-korea-utara', 'nuklir-korea-utara', 'korea-selatan', 'amerika-serikat', 'latihan-bersama-korea-selatan-dan-amerika-serikat'],
        }
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, display_id)

        json_data = self._download_json(
            'https://apidam.jixie.io/api/public/stream', display_id,
            query={'metadata': 'full', 'video_id': video_id})['data']

        formats, subtitles = [], {}
        for stream in json_data['streams']:
            if stream.get('type') == 'HLS':
                fmt, sub = self._extract_m3u8_formats_and_subtitles(stream.get('url'), display_id, ext='mp4')
                formats.extend(fmt)
                self._merge_subtitles(sub, target=subtitles)
            else:
                formats.append({
                    'url': stream.get('url'),
                    'width': stream.get('width'),
                    'height': stream.get('height'),
                    'ext': 'mp4',
                })

        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': json_data.get('title') or self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': (clean_html(traverse_obj(json_data, ('metadata', 'description')))
                            or self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage)),
            'thumbnails': traverse_obj(json_data, ('metadata', 'thumbnails')),
            'thumbnail': traverse_obj(json_data, ('metadata', 'thumbnail')),
            'duration': float_or_none(traverse_obj(json_data, ('metadata', 'duration'))),
            'has_drm': json_data.get('drm'),
            'tags': str_or_none(traverse_obj(json_data, ('metadata', 'keywords')), '').split(',') or None,
            'categories': str_or_none(traverse_obj(json_data, ('metadata', 'categories')), '').split(',') or None,
            'uploader_id': json_data.get('owner_id'),
        }


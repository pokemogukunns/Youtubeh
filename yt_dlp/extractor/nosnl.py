from .common import InfoExtractor
from ..utils import parse_duration, parse_iso8601, traverse_obj


class NOSNLArticleIE(InfoExtractor):
    _VALID_URL = r'https?://nos\.nl/((?!video)(\w+/)?\w+/)\d+-(?P<display_id>[\w-]+)'
    _TESTS = [
        {
            # only 1 video
            'url': 'https://nos.nl/nieuwsuur/artikel/2440353-verzakking-door-droogte-dreigt-tot-een-miljoen-kwetsbare-huizen',
            'info_dict': {
                'id': '2440340',
                'ext': 'mp4',
                'description': 'md5:5f83185d902ac97af3af4bed7ece3db5',
                'title': '\'We hebben een huis vol met scheuren\'',
                'duration': 95.0,
            }
        }, {
            # more than 1 video
            'url': 'https://nos.nl/artikel/2440409-vannacht-sliepen-weer-enkele-honderden-asielzoekers-in-ter-apel-buiten',
            'info_dict': {
                'id': '2440409',
                'title': 'Vannacht sliepen weer enkele honderden asielzoekers in Ter Apel buiten',
                'description': 'Er werd wel geprobeerd om kwetsbare migranten onderdak te bieden, zegt het COA.'
            },
            'playlist_count': 2,
        }, {
            # audio + video
            'url': 'https://nos.nl/artikel/2440789-wekdienst-16-8-groningse-acties-tien-jaar-na-zware-aardbeving-femke-bol-in-actie-op-ek-atletiek',
            'info_dict': {
                'id': '2440789',
                'title': 'Wekdienst 16/8: Groningse acties tien jaar na zware aardbeving • Femke Bol in actie op EK atletiek ',
                'description': 'Nieuws, weer, verkeer: met dit overzicht begin je geïnformeerd aan de dag.',
            },
            'playlist_count': 2,
        },
    ]

    def _get_video_generator(self, nextjs_json, display_id):
        for item in nextjs_json['items']:
            if item.get('type') == 'video':
                formats, subtitle = self._extract_m3u8_formats_and_subtitles(
                    traverse_obj(item, ('source', 'url')), display_id, ext='mp4')
                yield {
                    'id': str(item['id']),
                    'title': item.get('title'),
                    'description': item.get('description'),
                    'formats': formats,
                    'subtitles': subtitle,
                    'duration': parse_duration(item.get('duration')),
                }

            elif item.get('type') == 'audio':
                yield {
                    'id': str(item['id']),
                    'title': item.get('title'),
                    'url': traverse_obj(item, ('media', 'src')),
                    'ext': 'mp3',
                }

    def _real_extract(self, url):
        display_id = self._match_valid_url(url).group('display_id')
        webpage = self._download_webpage(url, display_id)

        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['data']
        return self.playlist_result(
            self._get_video_generator(nextjs_json, display_id),
            str(nextjs_json['id']),
            title=nextjs_json.get('title') or self._html_search_meta(['title', 'og:title', 'twitter:title'], webpage),
            description=nextjs_json.get('description') or self._html_search_meta(['description', 'twitter:description', 'og:description'], webpage),
            tags=nextjs_json.get('keyword'),
            modified_timestamp=parse_iso8601(nextjs_json.get(nextjs_json.get('modifiedAt'))))

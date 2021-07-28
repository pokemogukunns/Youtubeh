from __future__ import unicode_literals

from .theplatform import ThePlatformFeedIE
from ..utils import (
    ExtractorError,
    int_or_none,
    find_xpath_attr,
    xpath_element,
    xpath_text,
    update_url_query,
)


class CBSBaseIE(ThePlatformFeedIE):
    def _parse_smil_subtitles(self, smil, namespace=None, subtitles_lang='en'):
        subtitles = {}
        for k, ext in [('sMPTE-TTCCURL', 'tt'), ('ClosedCaptionURL', 'ttml'), ('webVTTCaptionURL', 'vtt')]:
            cc_e = find_xpath_attr(smil, self._xpath_ns('.//param', namespace), 'name', k)
            if cc_e is not None:
                cc_url = cc_e.get('value')
                if cc_url:
                    subtitles.setdefault(subtitles_lang, []).append({
                        'ext': ext,
                        'url': cc_url,
                    })
        return subtitles


class CBSIE(CBSBaseIE):
    _VALID_URL = r'''(?x)
        (?:
            cbs:|
            https?://(?:www\.)?(?:
                (?:cbs|paramountplus)\.com/(?:shows/[^/]+/video|movies/[^/]+)/|
                colbertlateshow\.com/(?:video|podcasts)/)
        )(?P<id>[\w-]+)'''

    _TESTS = [{
        'url': 'https://www.cbs.com/shows/garth-brooks/video/_u7W953k6la293J7EPTd9oHkSPs6Xn6_/connect-chat-feat-garth-brooks/',
        'info_dict': {
            'id': '_u7W953k6la293J7EPTd9oHkSPs6Xn6_',
            'ext': 'mp4',
            'title': 'Connect Chat feat. Garth Brooks',
            'description': 'Connect with country music singer Garth Brooks, as he chats with fans on Wednesday November 27, 2013. Be sure to tune in to Garth Brooks: Live from Las Vegas, Friday November 29, at 9/8c on CBS!',
            'duration': 1495,
            'timestamp': 1385585425,
            'upload_date': '20131127',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        '_skip': 'Blocked outside the US',
    }, {
        'url': 'http://colbertlateshow.com/video/8GmB0oY0McANFvp2aEffk9jZZZ2YyXxy/the-colbeard/',
        'only_matching': True,
    }, {
        'url': 'http://www.colbertlateshow.com/podcasts/dYSwjqPs_X1tvbV_P2FcPWRa_qT6akTC/in-the-bad-room-with-stephen/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/shows/all-rise/video/QmR1WhNkh1a_IrdHZrbcRklm176X_rVc/all-rise-space/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/movies/million-dollar-american-princesses-meghan-and-harry/C0LpgNwXYeB8txxycdWdR9TjxpJOsdCq',
        'only_matching': True,
    }]

    def _extract_video_info(self, content_id, site='cbs', mpx_acc=2198311517):
        items_data = self._download_xml(
            'https://can.cbs.com/thunder/player/videoPlayerService.php',
            content_id, query={'partner': site, 'contentId': content_id})
        video_data = xpath_element(items_data, './/item')
        title = xpath_text(video_data, 'videoTitle', 'title') or xpath_text(video_data, 'videotitle', 'title')
        tp_path = 'dJ5BDC/media/guid/%d/%s' % (mpx_acc, content_id)
        tp_release_url = 'https://link.theplatform.com/s/' + tp_path

        asset_types = []
        subtitles = {}
        formats = []
        useXMLmetadata = True
        last_e = None
        for item in items_data.findall('.//item'):
            asset_type = xpath_text(item, 'assetType')
            query = {
                'mbr': 'true',
                'assetTypes': asset_type,
            }
            if not asset_type:
                # fallback for content_ids that videoPlayerService doesn't return anything for
                # Examples:
                # https://www.paramountplus.com/shows/catdog/video/Oe44g5_NrlgiZE3aQVONleD6vXc8kP0k/catdog-climb-every-catdog-the-canine-mutiny/
                # https://www.paramountplus.com/shows/tooning-out-the-news/video/6hSWYWRrR9EUTz7IEe5fJKBhYvSUfexd/7-23-21-week-in-review-rep-jahana-hayes-howard-fineman-sen-michael-bennet-sheera-frenkel-cecilia-kang-/
                # https://www.cbs.com/shows/the-late-show-with-stephen-colbert/video/60icOhMb9NcjbcWnF_gub9XXHdeBcNk2/the-late-show-6-23-21-christine-baranski-joy-oladokun- (Expired)
                useXMLmetadata = False
                asset_type = 'fallback'
                formatList = ['M3U+none,MPEG4,M3U+appleHlsEncryption', 'MPEG4,M3U']
                currentIndex = 0
                query['formats'] = formatList[currentIndex]
                del query['assetTypes']
            if asset_type in asset_types or 'HLS_FPS' in asset_type or 'DASH_CENC' in asset_type or '':
                continue
            asset_types.append(asset_type)
            if asset_type.startswith('HLS') or asset_type in ('OnceURL', 'StreamPack'):
                query['formats'] = 'MPEG4,M3U'
            elif asset_type in ('RTMP', 'WIFI', '3G'):
                query['formats'] = 'MPEG4,FLV'
            try:
                tp_formats, tp_subtitles = self._extract_theplatform_smil(
                    update_url_query(tp_release_url, query), content_id,
                    'Downloading %s SMIL data' % asset_type)
            except ExtractorError as e:
                if not useXMLmetadata and currentIndex + 1 is not len(formatList):
                    query['formats'] = formatList[currentIndex + 1]
                    tp_formats, tp_subtitles = self._extract_theplatform_smil(
                        update_url_query(tp_release_url, query), content_id,
                        'Downloading %s SMIL data, trying again with another format' % asset_type)
                last_e = e
                continue
            formats.extend(tp_formats)
            subtitles = self._merge_subtitles(subtitles, tp_subtitles)
        if last_e and not formats:
            raise last_e
        self._sort_formats(formats)

        info = self._extract_theplatform_metadata(tp_path, content_id)
        info.update({
            'formats': formats,
            'subtitles': subtitles,
            'id': content_id
        })
        if useXMLmetadata:
            info.update({
                'title': title,
                'series': xpath_text(video_data, 'seriesTitle'),
                'season_number': int_or_none(xpath_text(video_data, 'seasonNumber')),
                'episode_number': int_or_none(xpath_text(video_data, 'episodeNumber')),
                'duration': int_or_none(xpath_text(video_data, 'videoLength'), 1000),
                'thumbnail': xpath_text(video_data, 'previewImageURL')
            })
        return info

    def _real_extract(self, url):
        content_id = self._match_id(url)
        return self._extract_video_info(content_id)

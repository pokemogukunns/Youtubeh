import itertools
from urllib.error import HTTPError

from .common import InfoExtractor
from .vimeo import VimeoIE

from ..compat import compat_urllib_parse_unquote
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    KNOWN_EXTENSIONS,
    mimetype2ext,
    parse_iso8601,
    str_or_none,
    try_get,
    url_or_none, traverse_obj, merge_dicts, ExtractorError,
)


class PatreonBaseIE(InfoExtractor):
    # FIXME: user-supplied user agent should override request user-agents
    USER_AGENT = 'Patreon/7.6.28'  # should we add a random generation for this?

    def _call_api(self, ep, item_id, query=None, headers=None, fatal=True, note=None):
        if headers is None:
            headers = {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = self.USER_AGENT

        try:
            return self._download_json(
                f'https://www.patreon.com/api/{ep}',
                item_id, note='Downloading API JSON' if not note else note,
                query=query, fatal=fatal, headers=headers)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                if e.cause.code == 403:
                    error_response = e.cause.read().decode('utf-8')
                    error_json = self._parse_json(error_response, None, fatal=False)
                    if error_json:
                        message = traverse_obj(error_json, ('errors', ..., 'detail'), get_all=False)
                        if message:
                            raise ExtractorError(f'Patreon said: {message}', expected=True)

                    elif 'cloudflare' in e.cause.headers.get('Server') and 'window._cf_chl_opt' in error_response:
                        raise ExtractorError('Unable to download video due to cloudflare captcha')


class PatreonIE(PatreonBaseIE):
    _VALID_URL = r'https?://(?:www\.)?patreon\.com/(?:creation\?hid=|posts/(?:[\w-]+-)?)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.patreon.com/creation?hid=743933',
        'md5': 'e25505eec1053a6e6813b8ed369875cc',
        'info_dict': {
            'id': '743933',
            'ext': 'mp3',
            'title': 'Episode 166: David Smalley of Dogma Debate',
            'description': 'md5:713b08b772cd6271b9f3906683cfacdf',
            'uploader': 'Cognitive Dissonance Podcast',
            'thumbnail': 're:^https?://.*$',
            'timestamp': 1406473987,
            'upload_date': '20140727',
            'uploader_id': '87145',
        },
    }, {
        'url': 'http://www.patreon.com/creation?hid=754133',
        'md5': '3eb09345bf44bf60451b8b0b81759d0a',
        'info_dict': {
            'id': '754133',
            'ext': 'mp3',
            'title': 'CD 167 Extra',
            'uploader': 'Cognitive Dissonance Podcast',
            'thumbnail': 're:^https?://.*$',
        },
        'skip': 'Patron-only content',
    }, {
        'url': 'https://www.patreon.com/creation?hid=1682498',
        'info_dict': {
            'id': 'SU4fj_aEMVw',
            'ext': 'mp4',
            'title': 'I\'m on Patreon!',
            'uploader': 'TraciJHines',
            'thumbnail': 're:^https?://.*$',
            'upload_date': '20150211',
            'description': 'md5:c5a706b1f687817a3de09db1eb93acd4',
            'uploader_id': 'TraciJHines',
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        }
    }, {
        'url': 'https://www.patreon.com/posts/episode-166-of-743933',
        'only_matching': True,
    }, {
        'url': 'https://www.patreon.com/posts/743933',
        'only_matching': True,
    }, {
        'url': 'https://www.patreon.com/posts/kitchen-as-seen-51706779',
        'md5': '96656690071f6d64895866008484251b',
        'info_dict': {
            'id': '555089736',
            'ext': 'mp4',
            'title': 'KITCHEN AS SEEN ON DEEZ NUTS EXTENDED!',
            'uploader': 'Cold Ones',
            'thumbnail': 're:^https?://.*$',
            'upload_date': '20210526',
            'description': 'md5:557a409bd79d3898689419094934ba79',
            'uploader_id': '14936315',
        },
        'skip': 'Patron-only content'
    }, {
        # m3u8 video (https://github.com/yt-dlp/yt-dlp/issues/2277)
        'url': 'https://www.patreon.com/posts/video-sketchbook-32452882',
        'info_dict': {
            'id': '32452882',
            'ext': 'mp4',
            'comment_count': int,
            'uploader_id': '4301314',
            'like_count': int,
            'timestamp': 1576696962,
            'upload_date': '20191218',
            'thumbnail': r're:^https?://.*$',
            'uploader_url': 'https://www.patreon.com/loish',
            'description': 'md5:e2693e97ee299c8ece47ffdb67e7d9d2',
            'title': 'VIDEO // sketchbook flipthrough',
            'uploader': 'Loish ',
        }
    }]

    # Currently Patreon exposes download URL via hidden CSS, so login is not
    # needed. Keeping this commented for when this inevitably changes.
    '''
    def _perform_login(self, username, password):
        login_form = {
            'redirectUrl': 'http://www.patreon.com/',
            'email': username,
            'password': password,
        }

        request = sanitized_Request(
            'https://www.patreon.com/processLogin',
            compat_urllib_parse_urlencode(login_form).encode('utf-8')
        )
        login_page = self._download_webpage(request, None, note='Logging in')

        if re.search(r'onLoginFailed', login_page):
            raise ExtractorError('Unable to login, incorrect username and/or password', expected=True)

    '''

    def _real_extract(self, url):
        video_id = self._match_id(url)
        post = self._call_api(f'posts/{video_id}', video_id, query={
                'fields[media]': 'download_url,mimetype,size_bytes',
                'fields[post]': 'comment_count,content,embed,image,like_count,post_file,published_at,title,current_user_can_view',
                'fields[user]': 'full_name,url',
                'json-api-use-default-includes': 'false',
                'include': 'media,user',
            })
        attributes = post['data']['attributes']
        title = attributes['title'].strip()
        image = attributes.get('image') or {}
        info = {
            'id': video_id,
            'title': title,
            'description': clean_html(attributes.get('content')),
            'thumbnail': image.get('large_url') or image.get('url'),
            'timestamp': parse_iso8601(attributes.get('published_at')),
            'like_count': int_or_none(attributes.get('like_count')),
            'comment_count': int_or_none(attributes.get('comment_count')),
        }
        can_view_post = traverse_obj(attributes, 'current_user_can_view')
        if can_view_post and info['comment_count']:
            info['__post_extractor'] = self.extract_comments(video_id)

        for i in post.get('included', []):
            i_type = i.get('type')
            if i_type == 'media':
                media_attributes = i.get('attributes') or {}
                download_url = media_attributes.get('download_url')
                ext = mimetype2ext(media_attributes.get('mimetype'))
                if download_url and ext in KNOWN_EXTENSIONS:
                    return merge_dicts({
                        'ext': ext,
                        'filesize': int_or_none(media_attributes.get('size_bytes')),
                        'url': download_url,
                    }, info)
            elif i_type == 'user':
                user_attributes = i.get('attributes')
                if user_attributes:
                    info.update({
                        'uploader': user_attributes.get('full_name'),
                        'uploader_id': str_or_none(i.get('id')),
                        'uploader_url': user_attributes.get('url'),
                    })

        # handle Vimeo embeds
        if try_get(attributes, lambda x: x['embed']['provider']) == 'Vimeo':
            embed_html = try_get(attributes, lambda x: x['embed']['html'])
            v_url = url_or_none(compat_urllib_parse_unquote(
                self._search_regex(r'(https(?:%3A%2F%2F|://)player\.vimeo\.com.+app_id(?:=|%3D)+\d+)', embed_html, 'vimeo url', fatal=False)))
            if v_url:
                return merge_dicts({
                    '_type': 'url_transparent',
                    'url': VimeoIE._smuggle_referrer(v_url, 'https://patreon.com'),
                    'ie_key': 'Vimeo',
                }, info)

        embed_url = try_get(attributes, lambda x: x['embed']['url'])
        if embed_url:
            return merge_dicts({
                '_type': 'url',
                'url': embed_url,
            }, info)

        post_file = traverse_obj(attributes, 'post_file')
        if post_file:
            name = post_file.get('name')
            ext = determine_ext(name)
            if ext in KNOWN_EXTENSIONS:
                return merge_dicts({
                    'ext': ext,
                    'url': post_file['url'],
                }, info)
            elif name == 'video':
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(post_file['url'], video_id)
                return merge_dicts(
                    {
                        'formats': formats,
                        'subtitles': subtitles,
                    }, info
                )

        if can_view_post is False:
            self.raise_no_formats('You do not have access to this post', video_id)
        else:
            self.raise_no_formats('post has no supported media', video_id)
        return info

    def _get_comments(self, post_id):
        cursor = None
        count = 0
        # Replies are grabbed in the same request.
        # When this breaks, need to add support for comments/post_id/replies ep

        params = {
            'page[count]': 50,
            'include': 'parent.commenter.campaign,parent.post.user,parent.post.campaign.creator,parent.replies.parent,parent.replies.commenter.campaign,parent.replies.post.user,parent.replies.post.campaign.creator,commenter.campaign,post.user,post.campaign.creator,replies.parent,replies.commenter.campaign,replies.post.user,replies.post.campaign.creator,on_behalf_of_campaign',
            'fields[comment]': 'body,created,deleted_at,is_by_patron,is_by_creator,vote_sum,current_user_vote,reply_count',
            'fields[user]': 'image_url,full_name,url',
            'filter[flair]': 'image_tiny_url,name',
            'sort': '-created',
            'json-api-version': 1.0,
            'json-api-use-default-includes': 'false',
        }

        for page in itertools.count(1):

            params.update({'page[cursor]': cursor} if cursor else {})
            response = self._call_api(f'posts/{post_id}/comments', post_id, query=params, note='Downloading comments page %d' % page)
            cursor = None
            for comment in traverse_obj(response, (('data', ('included', lambda _, v: v['type'] == 'comment')), ...), default=[]):
                count += 1
                comment_id = comment.get('id')
                attributes = comment.get('attributes') or {}
                if comment_id is None:
                    continue
                author_id = traverse_obj(comment, ('relationships', 'commenter', 'data', 'id'))
                author_info = traverse_obj(
                        response, ('included', lambda k, v: v['id'] == author_id and v['type'] == 'user', 'attributes'),
                        get_all=False, expected_type=dict, default={})
                yield {
                    'id': comment_id,
                    'text': attributes.get('body'),
                    'timestamp': parse_iso8601(attributes.get('created')),
                    'parent': traverse_obj(comment, ('relationships', 'parent', 'data', 'id'), default='root'),
                    'author_is_uploader': attributes.get('is_by_creator'),
                    'author_id': author_id,
                    'author': author_info.get('full_name'),
                    'author_thumbnail': author_info.get('image_url'),
                }

            if count < traverse_obj(response, ('meta', 'count')):
                cursor = traverse_obj(response, ('data', -1, 'id'))

            if cursor is None:
                break


class PatreonUserIE(PatreonBaseIE):

    _VALID_URL = r'https?://(?:www\.)?patreon\.com/(?!rss)(?P<id>[-\w]+)'

    _TESTS = [{
        'url': 'https://www.patreon.com/dissonancepod/',
        'info_dict': {
            'title': 'dissonancepod',
        },
        'playlist_mincount': 68,
        'expected_warnings': 'Post not viewable by current user! Skipping!',
    }, {
        'url': 'https://www.patreon.com/dissonancepod/posts',
        'only_matching': True
    }, ]

    @classmethod
    def suitable(cls, url):
        return False if PatreonIE.suitable(url) else super(PatreonUserIE, cls).suitable(url)

    def _entries(self, campaign_id, user_id):
        cursor = None
        params = {
            'fields[campaign]': 'show_audio_post_download_links,name,url',
            'fields[post]': 'current_user_can_view,embed,image,is_paid,post_file,published_at,patreon_url,url,post_type,thumbnail_url,title',
            'filter[campaign_id]': campaign_id,
            'filter[is_draft]': 'false',
            'sort': '-published_at',
            'json-api-version': 1.0,
            'json-api-use-default-includes': 'false',
        }

        for page in itertools.count(1):

            params.update({'page[cursor]': cursor} if cursor else {})
            posts_json = self._call_api(f'posts', user_id, query=params, note='Downloading posts page %d' % page)

            cursor = try_get(posts_json, lambda x: x['meta']['pagination']['cursors']['next'])

            for post in posts_json.get('data') or []:
                yield self.url_result(url_or_none(try_get(post, lambda x: x['attributes']['patreon_url'])), 'Patreon')

            if cursor is None:
                break

    def _real_extract(self, url):

        user_id = self._match_id(url)
        webpage = self._download_webpage(url, user_id, headers={'User-Agent': self.USER_AGENT})
        campaign_id = self._search_regex(r'https://www.patreon.com/api/campaigns/(\d+)/?', webpage, 'Campaign ID')
        return self.playlist_result(self._entries(campaign_id, user_id), playlist_title=user_id)

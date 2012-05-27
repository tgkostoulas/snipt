from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models

from taggit.managers import TaggableManager
from taggit.utils import edit_string_for_tags

from markdown_deux import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from snipts.utils import slugify_uniquely

import datetime, md5


site = Site.objects.all()[0]

class Snipt(models.Model):
    """An individual Snipt."""

    user         = models.ForeignKey(User, blank=True, null=True)

    title        = models.CharField(max_length=255)
    slug         = models.SlugField(max_length=255, blank=True)
    custom_slug  = models.SlugField(max_length=255, blank=True)
    tags         = TaggableManager()

    lexer        = models.CharField(max_length=50)
    code         = models.TextField()
    stylized     = models.TextField(blank=True, null=True)
    embedded     = models.TextField(blank=True, null=True)
    line_count   = models.IntegerField(blank=True, null=True, default=None)

    key          = models.CharField(max_length=100, blank=True, null=True)
    public       = models.BooleanField(default=False)
    blog_post    = models.BooleanField(default=False)
    
    created      = models.DateTimeField(auto_now_add=True, editable=False)
    modified     = models.DateTimeField(auto_now=True, editable=False)
    publish_date = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify_uniquely(self.title, Snipt)

        if not self.key:
            self.key = md5.new(self.slug + str(datetime.datetime.now())).hexdigest()

        if self.lexer == 'markdown':
            self.stylized = markdown(self.code, 'default')
        else:
            self.stylized = highlight(self.code,
                                      get_lexer_by_name(self.lexer, encoding='UTF-8'),
                                      HtmlFormatter())
        self.line_count = len(self.code.split('\n'))

        if self.lexer == 'markdown':
            lexer_for_embedded = 'text'
        else:
            lexer_for_embedded = self.lexer

        embedded = highlight(self.code,
                             get_lexer_by_name(lexer_for_embedded, encoding='UTF-8'),
                             HtmlFormatter(
                                 style='native',
                                 noclasses=True,
                                 prestyles="""
                                     background-color: #1C1C1C;
                                     border-radius: 5px;
                                     color: #D0D0D0;
                                     display: block;
                                     font: 11px Monaco, monospace !important;
                                     margin: 0;
                                     overflow: auto;
                                     padding: 15px;
                                     -webkit-border-radius: 5px;
                                     -moz-border-radius: 5px;
                                     """))
        embedded = (embedded.replace("\\\"","\\\\\"")
                            .replace('\'','\\\'')
                            .replace("\\", "\\\\")
                            .replace('background: #202020', ''))
        self.embedded = embedded

        return super(Snipt, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):

        if self.custom_slug:
            return '/{}/'.format(self.custom_slug)

        if self.public:
            return '/{}/{}/'.format(self.user.username, self.slug)
        else:
            return '/{}/{}/?key={}'.format(self.user.username, self.slug, self.key)

    def get_full_absolute_url(self):
        if settings.DEBUG:
            root = 'http://snipt.localhost'
        else:
            root = 'https://snipt.net'
        return '{}/{}/{}/'.format(root, self.user.username, self.slug)

    def get_embed_url(self):
        return 'https://{}/embed/{}/'.format(site.domain, self.key)

    @property
    def sorted_tags(self):
        return self.tags.all().order_by('name')

    @property
    def tags_list(self):
        return edit_string_for_tags(self.tags.all())

    @property
    def lexer_name(self):
        if self.lexer == 'markdown':
            return 'Markdown'
        else:
            return get_lexer_by_name(self.lexer).name

class Favorite(models.Model):
    snipt = models.ForeignKey(Snipt)
    user  = models.ForeignKey(User)

    created  = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    
    def __unicode__(self):
        return u'{} favorited by {}'.format(self.snipt.title, self.user.username)

from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Event(models.Model):
    """Events model.

    Mozillians can apply to attend these events.
    """
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Application(models.Model):
    """Aplication model for Mozillians."""
    entry_id = models.IntegerField(default=0)
    number_of_events = models.IntegerField(default=1)
    event = models.ManyToManyField(Event, through='PreferredEvent')
    reasoning = models.TextField(blank=True, default='')
    impact = models.TextField(default='', blank=True)
    learning_areas = models.TextField(default='', blank=True)
    ideas = models.TextField(blank=True, default='')
    commitment_1 = models.TextField(blank=True, default='')
    functional_team = models.CharField(max_length=255, default='', blank=True)
    team_contact = models.CharField(max_length=255, default='', blank=True)
    participation_opportunities = models.TextField(default='', blank=True)
    commitment_2 = models.TextField(blank=True, default='')
    community = models.TextField(default='', blank=True)
    track_record = models.TextField(default='', blank=True)
    community_impact = models.TextField(default='', blank=True)
    commitment_3 = models.TextField(blank=True, default='')
    other = models.TextField(default='', blank=True)
    date = models.DateTimeField(null=True, blank=True)
    application_complete = models.BooleanField(default=False)
    recommendation_letter = models.CharField(max_length=255, default='',
                                             blank=True)

    def __str__(self):
        return unicode(self.entry_id)


@python_2_unicode_compatible
class PreferredEvent(models.Model):
    event = models.ForeignKey(Event)
    application = models.ForeignKey(Application)
    preferred = models.BooleanField(default=False)
    reason = models.TextField(blank=True, default='')

    def __str__(self):
        return u'{0} {1}'.format(self.event, self.application)


@python_2_unicode_compatible
class MozillianGroup(models.Model):
    """Mozillians tracking groups."""
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class MozillianProfile(models.Model):
    """Mozillians User Profile"""
    full_name = models.CharField(max_length=255)
    email = models.EmailField(default='')
    city = models.CharField(max_length=50, default='', blank=True)
    country = models.CharField(max_length=50, default='')
    ircname = models.CharField(max_length=50, default='')
    tracking_groups = models.ManyToManyField(
        MozillianGroup, related_name='mozillians_tracking')
    avatar_url = models.URLField(max_length=400, default='')
    bio = models.TextField(blank=True, default='')
    mozillian_username = models.CharField(max_length=100, default='')
    application = models.ForeignKey(Application, blank=True, null=True,
                                    on_delete=models.SET_NULL,
                                    related_name='applications')

    def __str__(self):
        return unicode(self.id)

    class Meta:
        ordering = ['country', 'full_name']

    def get_next_entry(self, qs=None):
        if not qs:
            qs = MozillianProfile.objects.all()

        length = qs.count()
        for index, item in enumerate(qs):
            if (item == self) and (index <= length-2):
                return qs[index+1]
        return False

    def get_previous_entry(self, qs=None):
        if not qs:
            qs = MozillianProfile.objects.all()

        for index, item in enumerate(qs):
            if (item == self) and (index > 0):
                return qs[index-1]
        return False

    @property
    def positive(self):
        return self.votes.filter(vote=1).count()

    @property
    def stellar(self):
        return self.votes.filter(vote=2).count()

    @property
    def negative(self):
        return self.votes.filter(vote=-1).count()

    @property
    def skip(self):
        return self.votes.filter(vote=0).count()


class Vote(models.Model):
    """Vote relational model."""
    voter = models.ForeignKey(User, related_name='user_votes')
    nominee = models.ForeignKey(MozillianProfile, related_name='votes')
    vote = models.IntegerField(default=0, choices=((0, 'Skip'),
                                                   (1, 'Probably'),
                                                   (2, 'Definitely'),
                                                   (-1, 'No')))

    def __unicode__(self):
        return u'%s %s' % (self.voter, self.nominee)

Implement campaigns in a new campaigns.py, following our domain terminology.
Provide `create_campaign(name, promos, ...)` with whatever fields our domain
definition of a campaign requires, and `campaign_active(campaign, on_date)`
returning whether the campaign can be used on that date (a datetime.date).
Add tests.
<!-- Co-Authored-By: Claude Fable 5 <noreply@anthropic.com> -->

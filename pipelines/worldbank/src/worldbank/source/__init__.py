"""The World Bank API: settings, HTTP client, response contracts and the extract run plan.

The only package that knows the World Bank (ADR-0021). Its contracts are enforced here, at the
boundary, before a run can be committed (ADR-0005, ADR-0020).
"""

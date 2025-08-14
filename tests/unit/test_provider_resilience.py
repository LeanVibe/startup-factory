from tools.ai_providers import AIProviderManager

class TimeoutErrorSim(Exception):
    pass


def test_provider_error_taxonomy_mapping_basic():
    from tools.ai_providers import classify_provider_error, ProviderErrorCategory
    assert classify_provider_error(TimeoutErrorSim()) == (ProviderErrorCategory.TIMEOUT, True)
    assert classify_provider_error(TimeoutError("boom")) == (ProviderErrorCategory.TIMEOUT, True)
    assert classify_provider_error(Exception("rate limit exceeded")) == (ProviderErrorCategory.RATE_LIMIT, True)
    assert classify_provider_error(Exception("unauthorized")) == (ProviderErrorCategory.AUTH, False)
    assert classify_provider_error(Exception("out of memory")) == (ProviderErrorCategory.OOM, True)
    assert classify_provider_error(Exception("dns failure")) == (ProviderErrorCategory.NETWORK, True)

"""Safe external model failures, independent of any application feature."""


class ModelProviderError(RuntimeError):
    """An upstream failure whose message is safe for the application to expose."""


class DeepSeekError(ModelProviderError):
    pass


class GeminiError(ModelProviderError):
    pass

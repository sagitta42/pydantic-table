class PydanticTableException(Exception):
    pass


class PydanticTalbeAlembicException(PydanticTableException):
    pass

class PydanticTableTypeError(TypeError):
    pass
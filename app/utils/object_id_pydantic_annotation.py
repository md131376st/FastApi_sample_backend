from typing import Any, Dict

from bson import ObjectId
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema, CoreSchema
from pydantic.json_schema import JsonSchemaValue

#
# class PyObjectId(ObjectId):
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate
#
#     @classmethod
#     def __get_pydantic_core_schema__(
#             cls, source_type: type, handler: GetCoreSchemaHandler
#     ) -> CoreSchema:
#         # Define the core schema for validation
#         return core_schema.general_after_validator_function(
#             cls.validate,
#             core_schema.str_schema(),
#         )
#
#     @classmethod
#     def __get_pydantic_json_schema__(
#             cls, core_schema: CoreSchema, handler: GetCoreSchemaHandler
#     ) -> JsonSchemaValue:
#         # Generate JSON schema representation for the PyObjectId
#         json_schema = handler(core_schema)
#         json_schema.update(type="string", example="60d21b4667d0d8992e610c85")
#         return json_schema
#
#     @classmethod
#     def validate(cls, v, field):
#         """Validate that the input is a valid ObjectId"""
#         if isinstance(v, ObjectId):
#             return str(v)  # Convert ObjectId to string for validation
#         if not ObjectId.is_valid(v):
#             raise ValueError(f"Invalid ObjectId: {v}")
#         return str(ObjectId(v))  # Convert valid ObjectId string back to string
#
#     @classmethod
#     def __modify_schema__(cls, field_schema):
#         field_schema.update(type="string")

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> Dict[str, Any]:
        json_schema = handler(schema)
        json_schema.update(type="string", example="507f1f77bcf86cd799439011")
        return json_schema

    @staticmethod
    def validate(v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError(f"Invalid ObjectId: {v}")

    @staticmethod
    def __serialize__(v: ObjectId, serializer: Any) -> str:
        return str(v)

    @classmethod
    def __get_validators__(cls):
        # Pydantic-compatible validator generator for backward compatibility
        yield cls.validate

    def __str__(self):
        return str(super().__str__())
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: tests/services/greet.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x1atests/services/greet.proto\x12\x08greet.v1"\x1c\n\x0cHelloRequest\x12\x0c\n\x04name\x18\x01'
    b' \x01(\t"\x1d\n\nHelloReply\x12\x0f\n\x07message\x18\x01'
    b' \x01(\t2\x93\x02\n\x07Greeter\x12:\n\x08SayHello\x12\x16.greet.v1.HelloRequest\x1a\x14.greet.v1.HelloReply"\x00\x12@\n\x0eSecureSayHello\x12\x16.greet.v1.HelloRequest\x1a\x14.greet.v1.HelloReply"\x00\x12\x45\n\x13TransactionSayHello\x12\x16.greet.v1.HelloRequest\x1a\x14.greet.v1.HelloReply"\x00\x12\x43\n\x11PersistedSayHello\x12\x16.greet.v1.HelloRequest\x1a\x14.greet.v1.HelloReply"\x00\x42\x13Z\x11greet/v1/go-greetb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "tests.services.greet_pb2", _globals)
if _descriptor._USE_C_DESCRIPTORS is False:
    DESCRIPTOR._options = None
    DESCRIPTOR._serialized_options = b"Z\021greet/v1/go-greet"
    _globals["_HELLOREQUEST"]._serialized_start = 40
    _globals["_HELLOREQUEST"]._serialized_end = 68
    _globals["_HELLOREPLY"]._serialized_start = 70
    _globals["_HELLOREPLY"]._serialized_end = 99
    _globals["_GREETER"]._serialized_start = 102
    _globals["_GREETER"]._serialized_end = 377
# @@protoc_insertion_point(module_scope)

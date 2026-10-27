"""Bounded same-source identity certificates; no State/history cache.

Published resident buffers are immutable. Ordinary PyTorch in-place operations
and views share detectable version counters; inference tensors without those
counters always fall back. Raw custom-kernel writes, ``.data`` mutation and
foreign storage writes bypass that contract and cannot be legitimized by these
metadata certificates. Such writes must never target a published buffer.

The reviewed formatters issue ordinary certificates after computing a complete
identity. Only the two reviewed recruitment transactions may publish a small
actual-source check after their key-excluded Event/RNG transforms. Dataclass
replacements and manual/foreign identities receive no certificate. Every miss
uses the original full authoritative calculation.
"""
from collections import OrderedDict
from dataclasses import dataclass,fields
import threading
import weakref

import torch

CAPACITY=32
_SOURCE_FIELDS=("records","lengths","sections","string_bytes","string_offsets","errors","suffix_usage")
_CONTEXT_FIELDS=("records","string_bytes","string_offsets")
_NUMBER_FIELDS=("words","offsets","bytes")


@dataclass(frozen=True)
class _SourceJsonCheck:
    required_bytes:object
    errors:object
    count:object
    batch_error:object


@dataclass(frozen=True)
class _PublishedSourceCheck:
    engine_keys:object
    state_json:_SourceJsonCheck
    committed:object


def _check_snapshot(check):
    if check is None:return (),[]
    if type(check) is not _PublishedSourceCheck:raise ValueError("Unknown private identity proof")
    metadata=(type(check),id(check),type(check.engine_keys),id(check.engine_keys),type(check.state_json),id(check.state_json))
    tensors=[getattr(check.engine_keys,field.name) for field in fields(check.engine_keys)]
    tensors.extend(getattr(check.state_json,field.name) for field in fields(check.state_json));tensors.append(check.committed)
    return metadata,tensors


def _method(value,name):
    method=getattr(value,name)
    function=getattr(method,"__func__",method)
    return id(function),id(getattr(function,"__code__",None))


def _metadata_value(value):
    if value is None or type(value) in (bool,int,str,bytes) or isinstance(value,type):return value
    if isinstance(value,torch.device):return ("device",value.type,value.index)
    if type(value) is tuple:return tuple(_metadata_value(item) for item in value)
    raise ValueError("Uncertifiable formatter/context metadata")


def _tensor_metadata(value):
    if not isinstance(value,torch.Tensor) or value.is_inference() or value.layout!=torch.strided:
        raise ValueError("Uncertifiable tensor")
    # These are host metadata queries, never device value reads or fences.
    return (value._version,value.data_ptr(),value.storage_offset(),tuple(value.shape),tuple(value.stride()),
            value.dtype,value.device,value.layout,value.requires_grad)


class _TensorStamp:
    def __init__(self,value):self.ref=weakref.ref(value);self.metadata=_tensor_metadata(value)
    def matches(self,value):return self.ref() is value and self.metadata==_tensor_metadata(value)


def _snapshot(formatter,result):
    from .resident_state_json import ResidentStateJson,StateIdentityBatch
    # Only independently reviewed concrete implementations may issue.
    approved=type(formatter) is ResidentStateJson
    if not approved:
        try:
            from .resident_state_json_parallel import ParallelUnitStateJson
            approved=type(formatter) is ParallelUnitStateJson
        except ImportError:pass
    if not approved:
        try:
            from .resident_state_json_fields import ParallelFieldStateJson
            approved=type(formatter) is ParallelFieldStateJson
        except ImportError:pass
    if not approved or type(result) is not StateIdentityBatch:
        raise ValueError("Foreign formatter or identity")
    source=result.source;context=source.context;numbers=formatter.number_context
    if formatter.state_context is not context or numbers.state_context is not context:
        raise ValueError("Foreign source/number context")
    native=context.native
    metadata=(id(source),id(context),id(native),id(numbers),type(formatter),
        context.identity,context.string_count,context.device,context.random_stream_ids,context.editor_implementation,
        native.schema,native.definition_fingerprint,native.rules_id,native.wire_context_fingerprint,native.string_count,
        formatter.fingerprint,formatter.rules_literal,formatter.digest_implementation,formatter.digest_group_size,
        getattr(formatter,"fragment_group_size",None),
        _method(formatter,"serialize"),_method(formatter,"outer_engine_json"),_method(formatter,"identities"))
    tensors=[getattr(source,name) for name in _SOURCE_FIELDS]
    tensors.extend(getattr(context,name) for name in _CONTEXT_FIELDS)
    tensors.extend(getattr(numbers,name) for name in _NUMBER_FIELDS);tensors.append(formatter.rules)
    for group in ("state_json","state_keys","engine_json","engine_keys"):
        value=getattr(result,group)
        metadata+=(type(value),id(value))
        tensors.extend(getattr(value,field.name) for field in fields(value))
    return _metadata_value(metadata),tensors


class _Certificate:
    def __init__(self,formatter,result,byte_capacity,on_collect,check=None):
        self.identity=weakref.ref(result,on_collect);self.owner=weakref.ref(formatter)
        self.byte_capacity=byte_capacity;self.metadata,tensors=_snapshot(formatter,result)
        self.check=check;self.check_metadata,private=_check_snapshot(check);tensors.extend(private)
        self.stamps=tuple(_TensorStamp(value) for value in tensors)
    def matches(self,formatter,result,source,byte_capacity):
        if self.owner() is not formatter or self.identity() is not result or result.source is not source or byte_capacity!=self.byte_capacity:
            return False
        metadata,tensors=_snapshot(formatter,result)
        check_metadata,private=_check_snapshot(self.check);tensors.extend(private)
        return metadata==self.metadata and check_metadata==self.check_metadata and len(tensors)==len(self.stamps) and all(
            stamp.matches(value) for stamp,value in zip(self.stamps,tensors,strict=True))


class _Registry:
    def __init__(self,formatter):
        self.owner=weakref.ref(formatter);self.entries=OrderedDict();self.lock=threading.RLock()
        self.hits=0;self.misses=0
    def issue(self,result,byte_capacity,*,check=None):
        owner=self.owner()
        if owner is None:return
        key=id(result);registry=weakref.ref(self)
        def collected(ref):
            current=registry()
            if current is not None:
                with current.lock:
                    entry=current.entries.get(key)
                    if entry is not None and entry.identity is ref:current.entries.pop(key,None)
        try:certificate=_Certificate(owner,result,byte_capacity,collected,check)
        except (AttributeError,TypeError,ValueError,RuntimeError,OverflowError):return
        with self.lock:
            self.entries[key]=certificate;self.entries.move_to_end(key)
            while len(self.entries)>CAPACITY:self.entries.popitem(last=False)
    def lookup(self,formatter,result,source,byte_capacity,*,record=True):
        with self.lock:
            certificate=self.entries.get(id(result));valid=False
            if certificate is not None:
                try:valid=certificate.matches(formatter,result,source,byte_capacity)
                except (AttributeError,TypeError,ValueError,RuntimeError,OverflowError):pass
            if valid:
                self.entries.move_to_end(id(result))
                if record:self.hits+=1
                return result if certificate.check is None else certificate.check
            if certificate is not None:self.entries.pop(id(result),None)
            if record:self.misses+=1
            return None


def _certify_authoritative(formatter,result,*,byte_capacity):
    """Private issuance seam called only by reference identities(), never rebind."""
    registry=getattr(formatter,"_source_identity_certificates",None)
    if not isinstance(registry,_Registry) or registry.owner() is not formatter:
        registry=_Registry(formatter);formatter._source_identity_certificates=registry
    registry.issue(result,byte_capacity)
    return result


def source_identity_check(formatter,source,expected,*,byte_capacity,reuse=False):
    """Reuse an exact certified result or perform the existing authoritative check.

    Exact allocation matching preserves every before-JSON required size/error.
    Capacity changes deliberately fall back instead of interpreting device sizes
    on the host. Published small proofs preserve actual-source flags/size even
    when the public expected identity is failure-masked. Its expected flags are
    still checked separately by the transaction. No generic rebind API exists.
    """
    if type(reuse) is not bool:raise TypeError("Certified source reuse must be an explicit bool")
    if reuse:
        registry=getattr(formatter,"_source_identity_certificates",None)
        if isinstance(registry,_Registry):
            cached=registry.lookup(formatter,expected,source,byte_capacity)
            if cached is not None:return cached
    return formatter.identities(source,byte_capacity=byte_capacity)


def _publication_inputs(formatter,published,*,before,before_expected,before_check,after_identity,event,byte_capacity):
    """Metadata-only validation shared by the two private trusted call sites."""
    from .resident_state_json import StateIdentityBatch
    from .resident_events import EventAppendResult
    registry=getattr(formatter,"_source_identity_certificates",None)
    if not isinstance(registry,_Registry) or registry.owner() is not formatter:return None
    if type(published) is not StateIdentityBatch or type(after_identity) is not StateIdentityBatch or type(event) is not EventAppendResult:return None
    source=published.source;after=after_identity.source
    if source.context is not before.context or after.context is not before.context or event.state.context is not before.context:return None
    if source.lane_count!=before.lane_count or after.lane_count!=before.lane_count:return None
    if event.identities.source is not event.state:return None
    if any(getattr(event.identities,name) is not getattr(after_identity,name) for name in ("state_json","state_keys","engine_json","engine_keys")):return None
    # Authoritative fallback checks are freshly certified full identities. A
    # previous publication supplies a small check keyed by its public expected.
    if type(before_check) is StateIdentityBatch:
        original=registry.lookup(formatter,before_check,before,byte_capacity,record=False)
    else:
        original=registry.lookup(formatter,before_expected,before,byte_capacity,record=False)
    if original is not before_check:return None
    if registry.lookup(formatter,after_identity,after,byte_capacity,record=False) is not after_identity:return None
    return registry


def _small_publication_check(before_check,after_identity,committed):
    """Copy only small authoritative fields, never JSON/source/history buffers."""
    from .content_digest_metal import DigestBatch
    if not isinstance(committed,torch.Tensor) or committed.dtype!=torch.bool or tuple(committed.shape)!=():
        raise ValueError("Trusted publication needs the exact scalar commit predicate")
    def choose(left,right):
        if left.dtype!=right.dtype or left.shape!=right.shape or left.device!=right.device or left.device!=committed.device:
            raise ValueError("Trusted publication check layout differs")
        return torch.where(committed,left,right)
    keys=DigestBatch(**{field.name:choose(getattr(after_identity.engine_keys,field.name),getattr(before_check.engine_keys,field.name))
        for field in fields(DigestBatch)})
    state=_SourceJsonCheck(**{field.name:choose(getattr(after_identity.state_json,field.name),getattr(before_check.state_json,field.name))
        for field in fields(_SourceJsonCheck)})
    return _PublishedSourceCheck(keys,state,committed)


def _certify_recruitment_action_publication(formatter,published,*,before,before_expected,before_check,
                                           after_identity,event,committed,byte_capacity):
    """Private final ACTION path only: original after identity then Event+publish."""
    registry=_publication_inputs(formatter,published,before=before,before_expected=before_expected,before_check=before_check,
        after_identity=after_identity,event=event,byte_capacity=byte_capacity)
    if registry is not None:
        check=_small_publication_check(before_check,after_identity,committed)
        registry.issue(published,byte_capacity,check=check)
    return published


def _certify_recruitment_chance_publication(formatter,published,*,before,before_expected,before_check,
                                           after_identity,event,random,committed,byte_capacity):
    """Private final CHANCE path only: original after identity then Event+RNG."""
    from .resident_chance_io import ChanceRandomCommitResult
    if type(random) is not ChanceRandomCommitResult or random.state.context is not published.source.context:return published
    registry=_publication_inputs(formatter,published,before=before,before_expected=before_expected,before_check=before_check,
        after_identity=after_identity,event=event,byte_capacity=byte_capacity)
    if registry is not None:
        check=_small_publication_check(before_check,after_identity,committed)
        registry.issue(published,byte_capacity,check=check)
    return published

"""The implementation of common device based on provided SHV Tree."""
import asyncio
import inspect
import logging
import re
import typing

import shv

from .. import SHVNode, SHVTree

logger = logging.getLogger(__name__)


class SHVTreeDevice(shv.SimpleClient):
    """The SHV device that can respond on RPC requests based on given tree.

    The usage is very simple. You have to implement your own class that inherits
    this one. This class has to implement method for every method in the tree.
    Mapping of SHV method to the implementation method is done using its name
    where every non-word characters are replaced by '_' and a one '_' is
    prefixed (that is to make these methods protected in eyes of Python).

    Implementation methods can have any of these arguments with exactly these
    names:

    * ``param``: (:const:`shv.SHVType`) Parameters passed to the method.
    * ``access``: (:class:`shv.RpcMethodAccess`) Parameters passed to the method.
    * ``node``: (:class:`shvtree.SHVNode`) The SHV node this method is associated with.
    * ``method``: (:class:`shvtree.SHVMethod`) The SHV method representation of
      this method.
    * ``path``: (:class:`str`) Full path to the node in question.
    * ``node_name``: (:class:`str`) Name of the node (the last part of the `path`).
    * ``method_name``: (:class:`str`) Name of the method
    * ``method_path``: (:class:`str`) Full path to the node with method name
      appended by `:`.
    * ``signals``: (:class:`Signals`) Signals associated with this node. This
      allows you to trigger signals from methods.
    """

    tree: SHVTree | None = None
    """Tree presented by this device."""

    APP_NAME = "pyshvtree"

    def _ls(self, path: str) -> typing.Iterator[str]:
        yield from super()._ls(path)
        if self.tree is not None and (node := self.tree.get_node(path)) is not None:
            yield from (n.name for n in node.nodes.values())

    def _dir(self, path: str) -> typing.Iterator[shv.RpcMethodDesc]:
        yield from super()._dir(path)
        if self.tree is not None and (node := self.tree.get_node(path)) is not None:
            for m in node.methods.values():
                yield m.descriptor

    async def _method_call(
        self, path: str, method: str, access: shv.RpcMethodAccess, param: shv.SHVType
    ) -> shv.SHVType:
        args = {
            "path": path,
            "node_name": path.split("/")[-1],
            "method_name": method,
            "method_path": f"{path}:{method}",
            "access": access,
            "param": param,
        }
        impl = self._get_method_impl(args)
        if impl is None:
            return await super()._method_call(path, method, access, param)
        impl_param = inspect.signature(impl).parameters
        await self._pre_call(args)
        res = impl(**{key: value for key, value in args.items() if key in impl_param})
        if asyncio.iscoroutine(res):
            res = await res
        return await self._post_call(args, res)

    async def _pre_call(self, args: dict[str, typing.Any]) -> None:
        """This method is always called before method implementation is called.

        The default implementation is to check parameters and raises exception
        in case of a mismatch.

        You can modify ``args`` at this point before method is called.

        :param args: Arguments available to the method implementation.
        """
        if not args["method"].param.validate(args["param"]):
            raise shv.RpcInvalidParamsError("Invalid parameters were provided")

    async def _post_call(
        self, args: dict[str, typing.Any], result: shv.SHVType
    ) -> shv.SHVType:
        """This method is called after method implementation is called.

        The call to this method is not performed in case of exception.

        The default implementation returns result unchanged, it is checking its
        type and sends notification if method was ``set`` and node is property
        with signal.

        You can modify result if you need so in this method.

        :param args: Arguments available to the method implementation.
        :param result: Result provided by method.
        :return: Result that is sent as response to the request.
        """
        if not args["method"].result.validate(result):
            raise shv.RpcMethodCallExceptionError(
                f"Implementation produced result of invalid type: {str(result)}."
            )
        return result

    def _get_method_impl(
        self, args: dict[str, typing.Any]
    ) -> typing.Callable[..., shv.SHVType] | None:
        """Get method/function implementing given method on given path.

        The resolution of the name happens trough `_method_name`.

        Note that you can modify this method if you overload this class and this
        way you can add or modify the default behavior.

        This method can and should also modify the passed arguments to the
        method.

        :param args: Dictionary with arguments passed to the method when called
            later on. You can inspect it as well as modify to add additional
            arguments if you wish so.
        :return: None in case there is no implementation or function
          implementing this method.
        """
        if self.tree is None:
            return None
        path = args["path"]
        method_name = args["method_name"]
        node = self.tree.get_node(path)
        if node is None:
            return None
        method = node.methods.get(method_name, None)
        if method is None or method.access > args["access"]:
            return None
        signals = self.Signals(self.client, path, node)
        args.update({"node": node, "method": method, "signals": signals})
        return getattr(self, self._method_name(path, method_name), None)

    _method_name_re = re.compile(r"\W|^(?=\d)")

    @classmethod
    def _method_name(cls, path: str, method: str) -> str:
        """Map given generic method and path to the naming of it in this class.

        This method should not validate method or anything. It should only just
        provide mapping from method path to some possible method name. If you
        want to have smarter selection of methods then please override rather
        `_get_method_imp` instead.

        :param path: Path to the node method is associated with.
        :param method: Method to be converted to the Python method name.
        :return: Name of the method.
        """
        return cls._method_name_re.sub("_", f"_{path}_{method}")

    class Signals:
        """Provider of signal implementations.

        You need to use name of the signal method as attribute and it will
        provide you with coroutine that sends signal. This coroutine expects
        single parameter with SHV parameters.
        """

        def __init__(self, client: shv.RpcClient, path: str, node: SHVNode):
            self.__client = client
            self.__path = path
            self.__node = node

        def __getattr__(
            self, attr: str
        ) -> typing.Callable[
            [shv.SHVType], typing.Coroutine[typing.Any, typing.Any, None]
        ]:
            method = self.__node.methods.get(attr, None)
            if method is None or shv.RpcMethodFlags.SIGNAL not in method.flags:
                raise AttributeError

            async def func(value: shv.SHVType) -> None:
                assert method is not None
                if not method.result.validate(value):
                    raise RuntimeError("Attempting to send signal with invalid value.")
                await self.__client.send(
                    shv.RpcMessage.signal(self.__path, attr, value)
                )

            return func

    def signals(self, path: str) -> Signals:
        """Provides you with instance of :class:`Signals` for given path."""
        if self.tree is not None and (node := self.tree.get_node(path)) is not None:
            return self.Signals(self.client, path, node)
        raise ValueError(f"Path '{path}' is not valid in the provided tree.")

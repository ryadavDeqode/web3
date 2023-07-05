import logging
from typing import (
    Any,
    Dict,
    Iterable,
    Optional,
    Tuple,
    Union,
)

from eth_typing import (
    URI,
)
from eth_utils import (
    to_dict,
)

from web3._utils.http import (
    construct_user_agent,
)
from web3._utils.request import (
    cache_session,
    get_default_http_endpoint,
    make_post_request,
)
from web3.datastructures import (
    NamedElementOnion,
)
from web3.middleware import (
    http_retry_request_middleware,
)
from web3.types import (
    Middleware,
    RPCEndpoint,
    RPCResponse,
)

from .base import (
    JSONBaseProvider,
)
import requests
import re
import random

class HTTPProvider(JSONBaseProvider):
    logger = logging.getLogger("web3.providers.HTTPProvider")
    endpoint_uri = None
    _request_args = None
    _request_kwargs = None
    _endpoint_uris=None
    # type ignored b/c conflict with _middlewares attr on BaseProvider
    _middlewares: Tuple[Middleware, ...] = NamedElementOnion([(http_retry_request_middleware, 'http_retry_request')])  # type: ignore # noqa: E501

    def __init__(
        self, endpoint_uri: Optional[Union[URI, str]] = None,
            request_kwargs: Optional[Any] = None,
            session: Optional[Any] = None
    ) -> None:
        if endpoint_uri is None:
            self.endpoint_uri = get_default_http_endpoint()
        else:
            self.endpoint_uri = URI(endpoint_uri)

        self._request_kwargs = request_kwargs or {}

        if session:
            cache_session(self.endpoint_uri, session)
        self._endpoint_uris=fetch_rpc_from_chainlist()

        super().__init__()

    def __str__(self) -> str:
        return "RPC connection {0}".format(self.endpoint_uri)

    @to_dict
    def get_request_kwargs(self) -> Iterable[Tuple[str, Any]]:
        if 'headers' not in self._request_kwargs:
            yield 'headers', self.get_request_headers()
        for key, value in self._request_kwargs.items():
            yield key, value

    def get_request_headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'User-Agent': construct_user_agent(str(type(self))),
        }

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        self.logger.debug("Making request HTTP. URI: %s, Method: %s",
                          self.endpoint_uri, method)
        request_data = self.encode_rpc_request(method, params)
        endpoint_uri=self.get_random_url(self._endpoint_uris)
        if not endpoint_uri:
            endpoint_uri=self.endpoint_uri
        raw_response = make_post_request(
            endpoint_uri,
            request_data,
            **self.get_request_kwargs()
        )
        response = self.decode_rpc_response(raw_response)
        self.logger.debug("Getting response HTTP. URI: %s, "
                          "Method: %s, Response: %s",
                          self.endpoint_uri, method, response)
        return response
    
    def get_random_url(self,urls):
        if not urls:
            return None
        random_url = random.choice(urls)
        self.logger.debug("getting random urls- %s",random)
        return URI(random_url) 

def fetch_rpc_from_chainlist():
    url='https://chainlist.org/_next/data/3UduBZYW7UVz5riivJmbG/chain/42161.json?chain=42161'
    res=requests.get(url)
    data=res.json()
    rpcs_data=data['pageProps']['chain']['rpc']
    rpcs=[]
    pattern = re.compile(r"(?i).*api[_]?key.*")
    for rpc_data in rpcs_data:
        if not pattern.findall(rpc_data['url'].lower()): 
            rpcs.append(rpc_data['url'].lower())
    return rpcs

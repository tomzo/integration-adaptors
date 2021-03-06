import logging
from typing import Callable, Dict, Tuple
from tornado.httputil import HTTPServerRequest
from fake_spine.spine_response import SpineResponse

logger = logging.getLogger(__name__)


class RequestMatcher(object):

    def __init__(self, unique_identifier: str, matcher: Callable[[HTTPServerRequest], bool]):
        self.matcher = matcher
        self.unique_identifier = unique_identifier

    def does_match(self, request: HTTPServerRequest) -> bool:
        return self.matcher(request)


class SpineRequestResponseMapper(object):

    def __init__(self, request_matcher_to_response: Dict[RequestMatcher, SpineResponse]):
        self.request_matcher_to_response = request_matcher_to_response

    def response_for_request(self, request: HTTPServerRequest) -> Tuple[int, str]:
        for request_matcher, response in self.request_matcher_to_response.items():
            try:
                matches_response = request_matcher.does_match(request)
                if matches_response:
                    logger.log(logging.INFO,
                               f"request matched a configured matcher: {request_matcher.unique_identifier}")
                    return response.get_response()
            except Exception as e:
                logger.log(logging.ERROR, f"Matcher threw exception whilst trying to match: {e}")

        logger.log(logging.ERROR,
                   f"no matcher configured that matched request {request} with headers: {request.headers}")
        raise Exception(f"no response configured matching the request")

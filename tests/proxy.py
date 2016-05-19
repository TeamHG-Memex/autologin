from twisted.internet import reactor
from twisted.web import proxy, http


class ProxyRequest(proxy.ProxyRequest):
    def process(self):
        self.requestHeaders.addRawHeader(b'aproxy', b'yes')
        try:
            proxy.ProxyRequest.process(self)
        except KeyError:
            pass


class Proxy(proxy.Proxy):
    requestFactory = ProxyRequest


class ProxyFactory(http.HTTPFactory):
    def buildProtocol(self, addr):
        return Proxy()


PROXY_PORT = 8125


def main():
    http_port = reactor.listenTCP(PROXY_PORT, ProxyFactory())
    def print_listening():
        host = http_port.getHost()
        print('Proxy server running at http://{}:{}'.format(
            host.host, host.port))
    reactor.callWhenRunning(print_listening)
    reactor.run()


if __name__ == '__main__':
    main()

FROM nousresearch/hermes-agent@sha256:fcbe95482353e41cd30d39ddfc0f57ba3720f6da6969a7a69cdfb0d84b045cb6

USER root

COPY bootstrap-profile.sh /opt/transmuter/bootstrap-profile.sh
COPY transmuter_mcp_server.py /opt/transmuter/transmuter_mcp_server.py
COPY transmuter-profile /opt/transmuter/profile

RUN chmod +x /opt/transmuter/bootstrap-profile.sh

USER hermes

ENTRYPOINT ["/opt/transmuter/bootstrap-profile.sh"]
CMD ["gateway", "run"]

set +e
ollama --version
SHOULD_INSTALL=$?
set -e
if [ "$SHOULD_INSTALL" != "0" ]
then
    curl https://ollama.ai/install.sh | sh
fi
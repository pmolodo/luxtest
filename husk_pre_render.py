import os

# If we don't clear out the QT environment variables, the AdskLicensingAgent
# used by HtoA will error, which prevents it from getting the license
for key in os.environ:
    if key.startswith("QT_"):
        del os.environ[key]

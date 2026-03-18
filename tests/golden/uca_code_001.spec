rule @uca_code_001
trigger
    PythonREPL
check
    submit_post_request
    request_untrusted_source
enforce
    stop
end

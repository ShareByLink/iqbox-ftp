#class engine_tools:

#    @staticmethod
def isTemporaryFile (file_name_only):
    return file_name_only.startswith('~$') or \
           file_name_only.startswith('.~') or \
           (file_name_only.startswith('~') and file_name_only.endswith('.tmp'))
            
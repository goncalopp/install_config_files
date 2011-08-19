import os
import logging

DATA_EXTENSION= ".install_config_files_DATA"
DIR1= "."
DIR2= os.path.expanduser("~/")

def is_data_dir(d):
    n= len(DATA_EXTENSION)
    ret= (d[-n:]==DATA_EXTENSION)
    if ret:
        if not os.path.isdir(d):
            raise Exception( d+": a data file?? didn't think about a use case yet")
            
        logging.debug(d+" is a data directory")
    return ret

def test_and_remove_broken_link(d):
    if os.path.lexists(d) and not os.path.exists(d):
        logging.warn("Removing broken symlink: "+d)
        os.remove(d)

def analog_path(f):
    '''returns the equivalent path of the config file/dir in the home dir'''
    if is_data_dir(f):
        n= len(DATA_EXTENSION)
        f=f[:-n]
    return os.path.abspath(os.path.join(DIR2, f))

def backup_config_file(f):
    logging.warn("backing up "+f)
    os.rename(f, f+".config_backup")

def already_done(f1, f2):
    if os.path.islink(f2):
        tmp= os.readlink(f2)
        link_destination= tmp if os.path.isabs(tmp) else os.path.abspath(os.path.join(os.path.dirname(f2), tmp))
        if os.path.samefile(f1, link_destination):
            logging.info("a up-to-date symlink to config is present: "+f2)
            return True
    return False

def process_directory(d1):
    assert os.path.isdir(d1)
    logging.debug("processing directory "+d1)
    d2= analog_path( d1 )
    test_and_remove_broken_link(d2)
    if already_done(d1,d2):
        logging.warn("Link detected on directory, but the config files don't indicate it as a data directory. removing old link: "+d2)
        os.remove(d2)
    if not os.path.exists(d2):
        #if a directory doesn't exist, create it
        os.mkdir(d2)
    else:
        if not os.path.isdir(d2):
            #conflict: config has a directory, home has a plain file
            raise Exception("conflict: config has a directory, home has a plain file\n"+d2)
        pass    #dir in config has equivalent dir in home, do nothing

def process_file(f1):
    logging.debug("processing file "+f1)
    f2= analog_path(f1)
    test_and_remove_broken_link(f2)
    if already_done(f1,f2):
        return
    if not os.path.exists(f2):
        #config file doesn't yet exist on home, link it
        os.symlink(os.path.abspath(f1),f2)
    else:
        #config file already exists...
        backup_config_file(f2)
        os.symlink(os.path.abspath(f1),f2)


def recurse(basepath):
    assert os.path.isdir(basepath) #an equivalent base directory must already exist, now
    all_files= map(lambda x: os.path.join(basepath, x), sorted(os.listdir(basepath)))
    
    files= filter(os.path.isfile, all_files)
    directories= filter(os.path.isdir, all_files)
    
    for f in files:
        process_file( f )
    
    for d in directories:
        if is_data_dir(d):
            #if d is a data directory, treat is at a file
            process_file( d )
        else:
            process_directory( d )
            recurse(d)


if __name__=="__main__":
    assert "DIR1" in globals()
    assert "DIR2" in globals()
    if not os.path.isdir("config"):
        raise Exception( '''Must have "config" directory inside current dir, where the config files reside. Make sure your current directory is right''')
    os.chdir("config")
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:\t%(message)s')
    recurse(DIR1)
        

#!/usr/bin/python
import os, shutil
import logging

DATA_EXTENSION= ".install_config_files_DATA"
BACKUP_EXTENSION= ".config_backup"
DIR1= "."
DIR2= os.path.expanduser("~/")


class FileType(object):
    INEXISTENT, SYMLINK, FILE, DIRECTORY= range(4)
    
    def __init__(self, path):
        self._path= path
        self.detectFiletype()
        
    def detectFiletype(self):
        if not os.path.lexists(self._path):
            self.filetype= self.INEXISTENT
        elif os.path.islink( self._path ):
            self.filetype= self.SYMLINK
        elif os.path.isdir( self._path ):
            self.filetype= self.DIRECTORY
        elif os.path.isfile( self._path):
            self.filetype= self.FILE
        else:
            raise Exception("Unrecognized filetype: "+self._path)
            
    def __repr__(self):
        return self.path()
        
    def sort_key(self):
        '''for sorting, returns files in order: inexistent, links, files, dirs'''
        return self.filetype

    def isFile(self):
        return self.filetype==self.FILE

    def isDir(self):
        return self.filetype==self.DIRECTORY

    def isLink(self):
        return self.filetype==self.SYMLINK

    def exists(self):
        '''file exists, including broken links'''
        return not self.filetype==self.INEXISTENT

    def isBrokenLink(self):
        self.isLink() and os.path.lexists(self._path) and not os.path.exists(self._path) 

    def path(self):
        return self._path

    def final_path(self):
        '''absolute, follows symlinks'''
        p= self.path()
        if not self.isLink():
            p2= p
        else:
            tmp= os.readlink(p)
            p2= tmp if os.path.isabs(tmp) else os.path.join(os.path.dirname(f2), tmp)
        return os.path.abspath(p2)

    def sameFile(self, other):
        '''are, or link to, same file'''
        try:
            return os.path.samefile(self.final_path(), other.final_path())
        except:
            return False

    def mkdir(self):
        os.mkdir(self.path())
        self.filetype=DIRECTORY

    def rm(self):
        if self.isDir():
            shutil.rmtree(self.path())
        elif self.isFile() or self.isLink():
            os.remove(self.path())
        else:
            raise Exception("Can't remove this file type")
        self.filetype= self.INEXISTENT

    def mv(self, new, overwrite=True):
        if isinstance(new, basestring):
            new= self.__class__(new)
        assert isinstance(new, self.__class__)
        if overwrite and new.exists():
            new.rm()
        os.rename(self.path(), new.path())
        self.filetype= self.INEXISTENT
        return self.__class__(new.path())

    def ls(self, sort_by_type=False):
        '''returns objects for the files contained in this directory, sorted ASCIIbetically.
        Optionally sorts by filetype'''
        if not self.isDir():
            raise Exception("Doing ls() on a non-directory")
        p= self.path()
        paths= map(lambda x: os.path.join(p, x), sorted(os.listdir(p)))
        objects= map(self.__class__, paths)
        if sort_by_type:
            objects= sorted(objects, key= self.__class__.sort_key)
        return objects
    

class ConfigFile( FileType ):
    def isDataDir(self):
        '''is a data directory (see README)'''
        p= self.path()
        n= len(DATA_EXTENSION)
        if p[-n:]==DATA_EXTENSION:
            if not self.isDir():
                raise Exception( p+': Detected a "data directory" that is not a directory')
            logging.debug(p+" is a data directory")
            return True
        return False

    def analog(self):
        '''returns the equivalent path of the config file/dir in the home dir'''
        p= self.path()
        assert os.path.abspath(DIR1) in os.path.abspath(p)
        if self.isDataDir():
            p=p[:-len(DATA_EXTENSION)]
        other= self.__class__(os.path.abspath(os.path.join(DIR2, p)))
        #below: various checks before returning
        if self.isBrokenLink():
            self.rm()   
        if self.isDir() and (not self.isDataDir()) and self.alreadyDone(other):
            logging.warn("Up-to-date directory link detected on target, but the config files don't indicate it as a data directory. removing old link: "+other.path())
            other.rm()
        return other

    def isBackup(self):
        return BACKUP_EXTENSION == self.path()[:-len(BACKUP_EXTENSION)]

    def backup(self):
        p= self.path()
        np= p+BACKUP_EXTENSION
        if not self.exists():
            raise Exception("Trying to backup file that doesn't exist: "+p)
        if self.isBackup():
            raise Exception("Trying to backup a backup file: "+p)
        logging.warn("backing up "+p+" to "+np)
        self.mv(np)
        

    def alreadyDone(self, other=None):
        other= other or self.analog()
        if other.isLink() and self.sameFile(other):
            logging.info("up-to-date symlink present: "+other.path())
            return True
        return False

    def linkConfigFile(self, other=None):
        other= other or self.analog()
        p1= os.path.abspath(self.path())
        p2= other.path()
        os.symlink(p1, p2)



def process(f1):
    f2= f1.analog()
    if f1.isDir() and not f1.isDataDir():
        logging.debug("processing directory "+str(f1))
        if f2.exists():
            if f2.isDir():
                pass
            else:
                f2.backup()
        else:
            f2.mkdir()
    elif f1.isFile() or f1.isDataDir():
        logging.debug("processing file "+str(f1))
        if not f1.alreadyDone(f2):
            if f2.exists():
                f2.backup()
            f1.linkConfigFile(f2)
    else:
        raise Exception("Can't copy config file; not directory nor file (maybe a link?): "+str(f1))


def recurse(base):
    assert isinstance(base, ConfigFile)
    assert base.isDir() # must already exist, now
    files= base.ls(sort_by_type=False)
    
    for f in files:
        process(f)
        if f.isDir() and not f.isDataDir():
            recurse(f)


if __name__=="__main__":
    assert "DIR1" in globals()
    assert "DIR2" in globals()
    if not os.path.isdir("config"):
        raise Exception( '''Must have "config" directory inside current dir, where the config files reside. Make sure your current directory is right''')
    os.chdir("config")
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:\t%(message)s')
    DIR2= os.path.abspath(DIR2)
    recurse(ConfigFile(DIR1))
        

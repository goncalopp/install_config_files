#!/usr/bin/python
import os, shutil
import logging
import argparse

DATA_EXTENSION= ".install_config_files_DATA"
BACKUP_EXTENSION= ".config_backup"



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
        self.filetype= self.DIRECTORY

    def rm(self):
        if self.isDir():
            shutil.rmtree(self.path())
        elif self.isFile() or self.isLink():
            os.remove(self.path())
        else:
            raise Exception("Can't remove this file type")
        self.filetype= self.INEXISTENT

    def mv(self, new, overwrite=True):
        assert isinstance(new, basestring)
        new= FileType(new)
        if overwrite and new.exists():
            new.rm()
        os.rename(self.path(), new.path())
        self.filetype= self.INEXISTENT

    def ls(self, sort_by_type=False):
        '''returns objects for the files contained in this directory, sorted ASCIIbetically.
        Optionally sorts by filetype'''
        if not self.isDir():
            raise Exception("Doing ls() on a non-directory")
        p= self.path()
        paths= map(lambda x: os.path.join(p, x), sorted(os.listdir(p)))
        objects= map(FileType, paths)
        if sort_by_type:
            objects= sorted(objects, key= FileType.sort_key)
        return objects

    def analog(self, destination):
        '''let p be this file's relative path.
        This function returns the absolute path of p, relative to DESTINATION (instead of the cwd, as usual)'''
        p= self.path()
        assert not os.path.isabs(p)
        assert isinstance(destination, basestring)
        return os.path.abspath(os.path.join(destination, p))

class ConfigFile( FileType ):
    def isBackup(self):
        return self.path().endswith(BACKUP_EXTENSION)

    def backup(self):
        p= self.path()
        np= p+BACKUP_EXTENSION
        if not self.exists():
            raise Exception("Trying to backup file that doesn't exist: "+p)
        if self.isBackup():
            raise Exception("Trying to backup a backup file: "+p)
        logging.warn("backing up "+p+" to "+np)
        self.mv(np)



class ConfigFileDestination( ConfigFile ):
    def __init__(self, path, original):
        assert isinstance(original, ConfigFileOrigin)
        FileType.__init__(self, path)
        self.original= original
        if self.isBrokenLink():
            logging.warn("Removing broken link: "+str(self))
            self.rm()
        if original.isDir() and (not original.isDataDir()) and self.alreadyDone():
            logging.warn("Up-to-date directory link detected on target, but the config files don't indicate it as a data directory. removing old link: "+self.path())
            self.rm()

    def alreadyDone(self):
        if self.isLink() and self.sameFile(self.original):
            logging.info("up-to-date symlink present: "+self.path())
            return True
        return False


    def link(self):
        logging.info("linked "+self.path())
        p1= os.path.abspath(self.original.path())
        p2= self.path()
        os.symlink(p1, p2)


class ConfigFileOrigin( ConfigFile ):
    def __init__(self, path, installer):
        assert isinstance(installer, ConfigurationInstaller)
        self.installer= installer
        FileType.__init__(self, path)

    def isDataDir(self):
        result= self.path().endswith(DATA_EXTENSION)
        if result and not self.isDir():
            raise Exception( self.path()+': Detected a "data directory" that is not a directory')
        return result

    def analog(self):
        analog_path= FileType.analog(self, self.installer.destination)
        if self.isDataDir():
            analog_path= analog_path[:-len(DATA_EXTENSION)]
        return ConfigFileDestination( analog_path, self)

    def process(self):
        dest= self.analog()
        if self.isDir() and not self.isDataDir():
            logging.debug("processing directory "+str(self))
            if dest.exists():
                if dest.isDir():
                    pass
                else:
                    dest.backup()
            else:
                dest.mkdir()
        elif self.isFile() or self.isDataDir():
            logging.debug("processing file "+str(self))
            if not dest.alreadyDone():
                if dest.exists():
                    dest.backup()
                dest.link()
        else:
            raise Exception("Can't copy config file; not directory nor file (maybe a link?): "+str(self))



class ConfigurationInstaller:
    def __init__(self, source, destination):
        source, destination= os.path.abspath(source), os.path.abspath(destination)
        os.chdir( source ) #will make relative paths relative to source
        self.source= ConfigFileOrigin(".", self)
        self.destination= destination

    def do_it(self):
        self.recurse( self.source, self.destination )

    def recurse(self, source, destination):
        assert isinstance(source, ConfigFileOrigin)
        assert source.isDir() # must already exist, now
        files= source.ls(sort_by_type=False)
        for f in files:
            c= ConfigFileOrigin( f.path(), self )
            c.process()
            if c.isDir() and not c.isDataDir():
                self.recurse(c, destination)




if __name__=="__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:\t%(message)s')
    parser = argparse.ArgumentParser(description='''Links config files''')
    parser.add_argument('source')
    parser.add_argument('destination', nargs="?", default=os.path.expanduser("~/"))
        
    args= parser.parse_args()

    installer= ConfigurationInstaller( args.source, args.destination)
    installer.do_it()


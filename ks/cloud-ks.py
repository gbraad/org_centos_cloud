__author__ = 'asad'

import os.path
import urllib2
import sys
import tempfile
import shutil
from pyanaconda.addons import AddonData
from pyanaconda.constants import ROOT_PATH
from pyanaconda import iutil
from pykickstart.options import KSOptionParser
from pykickstart.errors import KickstartParseError, KickstartValueError,formatErrorMsg
from blivet import util


__all__ = ["Cloudks"]

ANSWERS_FILE = "/root/packstack-answers.txt"
GROUP_REQUIRED = ("@Cloud",)

# Mandatory methods (handle_header, handle_line, setup, execute and __str__)

class Cloudks(AddonData):

    def __init__(self, name):

        AddonData.__init__(self, name)
        self.lines = ""
        self.arguments = ""
        self.state = "none"

    # Creating %addon section in post-install anaconda.cfg file
    def __str__(self):
        addon_str = "%%addon %s " % self.name
        if self.state == "True":
            addon_str += ("--enable" + str (self.arguments) + "\n%%end\n")
        else:
            addon_str += ("--disable\n%%end\n" )
        #addon_str += "\n%s\n%%end\n" % self.lines
        return addon_str

    def handle_header(self, lineno, args):

        op = KSOptionParser()
        op.add_option("--enable", "-e", action="store_true", default=False,
                      dest="state", help="Enable Cloud Support")
        op.add_option("--disable", "-d", action="store_false",
                      dest="state", help="(Default) Disable Cloud Support")
        op.add_option("--allinone", "-a", action="store_true", default=True,
                      dest="mode", help="Specify the mode of Packstack Installation")
        op.add_option("--answer-file","-f", action="store",type= "string",
                      dest="file", help="Specify URL of answers file")
        (options, extra) = op.parse_args(args=args, lineno=lineno)

        # Error Handling
        if str(options.state) == "none":
            self.arguments = "none"
        elif str(options.state) == "True":
            self.state = str(options.state)
            if options.file and options.mode:
                msg = "options --allinone and --answer-file are mutually exclusive"
                raise KickstartParseError(msg)
            elif options.file:
                try:
                    response = urllib2.urlopen(options.file)
                    for line in response:
                        self.lines += line
                except urllib2.HTTPError, e:
                    msg = "Kickstart Error:: HTTPError: " + str(e.code)
                    raise KickstartParseError, formatErrorMsg(lineno, msg=msg)
                except urllib2.URLError, e:
                    msg = "Kickstart Error: HTTPError: " + str(e.reason)
                    raise KickstartParseError, formatErrorMsg(lineno, msg=msg)
                except:
                    msg = 'Exception Unable to fetch Answers file'
                    raise KickstartParseError, formatErrorMsg(lineno, msg=msg)
                self.arguments = "--answers-file = " + options.file
            elif options.mode:
                self.arguments = options.mode
            elif extra:
                msg = "Too many Arguments Specified"
                raise KickstartValueError, formatErrorMsg(lineno, msg=msg)
            else:
                self.arguments = "none"
        else:
            self.state = str(options.state)


    def handle_line(self, line):
        """
        We don't need to do any line handling unless we want to take packstack
        command line arguments in kickstart
        :param line:
        :return:

        """

        pass

    def finalize(self):
        """

        The finalize method that is called when the end of the %addon section
        (i.e. the %end line) is processed. An addon should check if it has all
        required data. If not, it may handle the case quietly or it may raise
        the KickstartValueError exception.

        """
        #TODO: Maybe do further error handling here
        # no actions needed in this addon
        pass

    def setup(self, storage, ksdata, instclass):

        """
        During installation just install the package group
        Cloud..
        """
        print ("I'm in ks setup")
        if self.state == "True":
            groups = list(GROUP_REQUIRED)
            for item in groups:
                if item not in ksdata.packages.packageList:
                    ksdata.packages.packageList.append(item)
                    # TODO: Copy CIRIOS image & rabbitmq certificate file at this stage.

        #pass

    def execute(self, storage, ksdata, instclass, users):
        """
        Post install activities, first copy the answer file
        from location given in kickstart. Second copy cirrios
        image and rabbitmq public key (both needed for offline packstack run)
        """
        # Create Answers file from given URL TODO:Copy the answer file directly
        if self.state == "True":
            if self.lines is not None:
                answer_file = os.path.normpath(ROOT_PATH + ANSWERS_FILE)
                with open(answer_file, "w") as fobj:
                    fobj.write("%s\n" % self.lines)

            # Copying cirrios image & rabbitmq public key to host system from media
            tmpdirectory = tempfile.mkdtemp()
            util.mount(device="/dev/disk/by-label/CentOS\\x207\\x20x86_64",mountpoint=tmpdirectory,fstype="auto")
            shutil.copy(tmpdirectory + "/Packages/RDO/cirros-0.3.1-x86_64-disk.img",
                        os.path.normcase(ROOT_PATH + "/root/cirros-0.3.1-x86_64-disk.img"))
            shutil.copy(tmpdirectory + "/Packages/RDO/rabbitmq-signing-key-public.asc",
                        os.path.normcase(ROOT_PATH + "/root/rabbitmq-signing-key-public.asc"))
            util.umount(tmpdirectory)
            shutil.rmtree(tmpdirectory)
            # Copy Addon itself to /usr/share/anaconda/addons
            print(ROOT_PATH)
            if os.path.exists(ROOT_PATH + "/usr/share/anaconda/addons/org_centos_cloud"):
                os.mkdir(ROOT_PATH + "/usr/share/anaconda/addons/org_centos_cloud")
            shutil.copytree("/usr/share/anaconda/addons/org_centos_cloud",
                            os.path.normcase(ROOT_PATH + "/usr/share/anaconda/addons/org_cent_cloud"))

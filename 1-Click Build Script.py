#!/usr/bin/python
#coding=utf-8

import os
import sys
from collections import namedtuple

class BuildError(Exception):pass

builds = []
buildedPaths = []

BuildParams = namedtuple("BuildParams", \
             ("name",                "path",                 "target",               "adhocCerName",         "appstoreCerName",  "configuration", "isHD",  "buildLite",  "afterBuild",  "beforeBuild"))

def addBuildParam(*kwarg):
    builds.append(BuildParams(*kwarg))

addBuildParam("pp",                 "proj.ios.pp",           "zhxy_pp",              "",                     "",                 "release",       True,    False,          "",            "")

def xcrun(buildData, appPath, endWith=""):
    xcrunShell = """
    xcrun -sdk iphoneos PackageApplication -v %s -o ~/Desktop/%s_%s%s.ipa
    """%(\
            appPath, \
            ipaName+buildData.name+('_HD' if buildData.isHD else '_LD'), \
            CFBundleShortVersionString, \
            endWith)

    if os.system(xcrunShell):
        raise BuildError

def xcodebuild_ipa(buildData):
    remove_adhoc = """
    rm ~/Desktop/%s_%s.ipa
    """%(\
            ipaName+buildData.name+'_adhoc'+('_HD' if buildData.isHD else '_LD'), \
            CFBundleShortVersionString)

    xcrunShell_adhoc = """
    xcodebuild -exportArchive -exportFormat ipa -archivePath "temp.xcarchive" -exportPath "~/Desktop/%s_%s.ipa" -exportProvisioningProfile %s
    """%(\
            ipaName+buildData.name+'_adhoc'+('_HD' if buildData.isHD else '_LD'), \
            CFBundleShortVersionString, \
            buildData.adhocCerName)

    remove_appstore = """
    rm ~/Desktop/%s_%s.ipa
    """%(\
            ipaName+buildData.name+'_appstore'+('_HD' if buildData.isHD else '_LD'), \
            CFBundleShortVersionString)

    xcrunShell_appstore = """
    xcodebuild -exportArchive -exportFormat ipa -archivePath "temp.xcarchive" -exportPath "~/Desktop/%s_%s.ipa" -exportProvisioningProfile %s
    """%(\
            ipaName+buildData.name+'_appstore'+('_HD' if buildData.isHD else '_LD'), \
            CFBundleShortVersionString, \
            buildData.appstoreCerName)

    os.system(remove_adhoc);
    if os.system(xcrunShell_adhoc):
        raise BuildError

    os.system(remove_appstore);
    if os.system(xcrunShell_appstore):
        raise BuildError

def changeVersion(fileName):
    #fr = open('Info.plist', 'r')
    fr = open(fileName, 'r')

    lines = fr.readlines()
    fr.close()

    #fw = open('Info.plist', 'w')
    fw = open(fileName, 'w')

    changeNextLine = False
    for line in lines:
        if changeNextLine:
            fw.write(line[:line.find('>')+1] + CFBundleShortVersionString + line[line.find('</'):])
            changeNextLine = False
        else:
            if 'CFBundleShortVersionString' in line:
                changeNextLine = True
            fw.write(line)
    fw.close()

def changeAppName(fileName, buildData):
    #fr = open('Info.plist', 'r')
    fr = open(fileName, 'r')

    lines = fr.readlines()
    fr.close()

    #fw = open('Info.plist', 'w')
    fw = open(fileName, 'w')

    changeNextLine = False
    for line in lines:
        if changeNextLine:
            fw.write(line[:line.find('>')+1] + CFBundleDisplayName + line[line.find('</'):])
            changeNextLine = False
        else:
            if 'CFBundleDisplayName' in line:
                changeNextLine = True
            fw.write(line)
    fw.close()

def buildAll(buildData):
    print "------------start build " + buildData.name + "------------";

    if buildData.beforeBuild != None:
        exec(buildData.beforeBuild)

    xcodebuildShell = """
    rm -r build/Release-iphoneos/
    #rm -r ../../cocos2dx/proj.ios/build/
    #xcodebuild clean -alltargets
    xcodebuild -target %s -configuration %s -jobs 4
    """ % (buildData.target, buildData.configuration)

    xcodebuildShell_cer = """
    rm -r ./temp.xcarchive
    xcodebuild -scheme %s archive -archivePath "temp.xcarchive" -jobs 4
    """ % (buildData.target)

    addLitePackShell = """
    find build/Release-iphoneos/ -name "*.app" | xargs -I {} touch {}/LitePack
    """

    removeLitePackShell = """
    find build/Release-iphoneos/ -name "LitePack" | xargs -I {} rm {}
    """

    addResShell_HD_lite = """
    find build/Release-iphoneos/ -name "*.app" | xargs -I {} cp -r ../fengmo {}
    """
    addResShell_LD_lite = """
    find build/Release-iphoneos/ -name "*.app" | xargs -I {} cp -r ../fengmo_small {}
    """
    addResShell_HD = """
    find build/Release-iphoneos/ -name "*.app" | xargs -I {} cp -r ../fengmo/* {}
    """
    addResShell_LD = """
    find build/Release-iphoneos/ -name "*.app" | xargs -I {} cp -r ../fengmo_small/* {}
    """

    os.chdir(buildData.path);
    #print('removing apps')
    #os.system("rm -r build/Release-iphoneos")

    for path, _, files in os.walk('.'):
        if path == ".":
            for filename in files:
                if filename.endswith('Info.plist'):
                    changeAppName(filename, buildData);
                    changeVersion(filename);

    if buildData.path not in buildedPaths:
        if os.system("find . -name 'project.pbxproj' | xargs -I {} python ../update_xcode_project.py {}"):
            raise BuildError
        buildedPaths.append(buildData.path)

    # 越狱 #####################################
    if buildData.adhocCerName == "":
        if os.system(xcodebuildShell):
            raise BuildError

        if buildData.buildLite:
            #build lite
            if os.system(addLitePackShell):
                raise BuildError

            for path, _, _ in os.walk('build/Release-iphoneos'):
                if path.endswith('.app'):
                    xcrun(buildData, path, '_lite')

            if os.system(removeLitePackShell):
                raise BuildError

            #build full
            if buildData.isHD:
                if os.system(addResShell_HD_lite):
                    raise BuildError
            else:
                if os.system(addResShell_LD_lite):
                    raise BuildError
        else:
            #build full
            if buildData.isHD:
                if os.system(addResShell_HD):
                    raise BuildError
            else:
                if os.system(addResShell_LD):
                    raise BuildError

        for path, _, _ in os.walk('build/Release-iphoneos'):
            if path.endswith('.app'):
                xcrun(buildData, path, '')

    # appstore #################################
    else:
        if os.system(xcodebuildShell_cer):
            raise BuildError

        xcodebuild_ipa(buildData)

    os.chdir("..");


if __name__ == "__main__":
    for buile in builds:
        try:
            buile = builds
            print buile
        except BuildError:
            print "build %s failed" % buile.name
            break;
    else:
        print ""
        sys.exit(0)
    sys.exit(1)

# Author: Luke Gane
# Tested on Windows 7 with Python 3.4 and ffmpeg-20160626-074fdf4-win64-static

import os
import re
import subprocess

# === START PARAMETERS ===

# Note: use forward slashes for paths

# Root folder containing directories for each sound class
path = 'C:/Directory of sound groups'

# Directories are assumed to be structured as follows:
# path
# |
# |- ### NAME OF GROUP
#    |- NAME OF FIRST SOUND.wav
#    |- NAME OF SECOND SOUND.wav
#    |- ...
#    |- transcript.txt (optional; one line per caption, one caption per sound file)
# |- ### NAME OF GROUP
# |- ...

# Directory where intermediate video files and concatenation file will be created
# These files will be deleted after the output file is created
outputVideoPath = 'C:/Videos'

# Path to FFmpeg
ffmpegPath = 'C:/ffmpeg-20160626-074fdf4-win64-static/bin/ffmpeg'

# Path to font (omit drive letter)
fontPath = '/Windows/Fonts/arialbd.ttf'

# Name of output file (no extension)
outputVideoName = 'output_video'

# === END PARAMETERS ===

# Settings for console output
tabSpaceCount = 4
showErrorOutput = True

def EscapeStringForFfmpeg(inputString):
    result = inputString
    # Regarding escaping of input to FFmpeg filters, see: https://ffmpeg.org/ffmpeg-filters.html#Notes-on-filtergraph-escaping

    # Basic escaping
    # At this level, special characters are: \':
    # TODO BUG a backslash in the original caption won't end up in the video
    result = re.sub("([\\':])", r"\\\1", result)

    # Escape filtergraph special characters (put a single backslash in front of each of them)
    # For list of filtergraph characters, see: https://ffmpeg.org/ffmpeg-filters.html#Filtergraph-syntax-1
    # Filtergraph special characters are: \'[]=;,
    result = re.sub(r"([\\'\[\]=;,])", r"\\\1", result)

    return result

soundDirs = os.listdir(path)

videoOutputFiles = [] # List of intermediate video files to concatenate
failedVideoOutputfiles = [] # List of intermediate video files that FFmpeg failed to generate (if any)

for curDir in soundDirs:

    dirMatch = re.match(r'(\d+) (.+)', curDir) # Expects subdirectory names to start with a number, followed by a space, then some description of the class of sounds contained within
    soundClassNumber = dirMatch.group(1)
    soundClassName = dirMatch.group(2)

    print('='*64)
    print('Sound class: ' + soundClassName)
    print('='*64)

    curDirPath = path + '/' + curDir
    
    if os.path.isdir(curDirPath):

        curFiles = os.listdir(curDirPath)

        curWavFiles = [name for name in curFiles if name.endswith('.wav')]

        isTranscriptAvailable = False;
        captions = [];
        try:
            curTranscriptFile = curFiles[curFiles.index('transcript.txt')];
            isTranscriptAvailable = True;
            with open(curDirPath + '/' + curTranscriptFile, 'r') as captionsFile:
                for line in captionsFile:
                    captions.append(line.rstrip())
        except ValueError:
            print(' '*tabSpaceCount + 'WARNING: No transcript file found for sound class ' + soundClassName + '; using file name as caption.')

        for curIndex in range(0,len(curWavFiles)):

            curWav = curWavFiles[curIndex]

            print(' '*tabSpaceCount + 'File: ' + curWav)
            print(' '*tabSpaceCount + '-'*60)
            
            curCommand = ffmpegPath + ' -i ' + '"' + curDirPath + '/' + curWav + '"';

            print(' '*tabSpaceCount*2 + 'Getting file duration...')
            
            ffmpegWavInfoString = '';
            try:
                output = subprocess.check_output([ffmpegPath, '-i', curDirPath + '/' + curWav], stderr=subprocess.STDOUT, universal_newlines=True)
                ffmpegWavInfoString = output
            except subprocess.CalledProcessError as e: # Expected that this exception will be thrown (FFmpeg complains that "[a]t least one output file must be specified").
                ffmpegWavInfoString = e.output

            matches = re.search(r"Duration:\s{1}(?P<hours>\d+?):(?P<minutes>\d+?):(?P<seconds>\d+\.\d+?),", ffmpegWavInfoString, re.DOTALL).groupdict()
            wavDuration = float(matches['hours'])*60*60 + float(matches['minutes'])*60 + float(matches['seconds']);

            print(' '*tabSpaceCount*2 + 'Duration: ' + str(wavDuration) + ' seconds')

            curVideoOutputFileName = soundClassNumber + '_' + str(curIndex) + '.mp4'
            curVideoOutputFilePath = outputVideoPath + '/' + curVideoOutputFileName

            curCaption = '';
            if isTranscriptAvailable:
                curCaption = captions[curIndex]
            else:
                curCaption = curWav

            print(' '*tabSpaceCount*2 + 'Caption: ' + curCaption)

            curVideoCommand = [ffmpegPath,
                               ' -y -f lavfi -i color=c=black:s=640x480 -i ',
                               '"' + curDirPath + '/' + curWav + '"',
                               ' -vf "drawtext=fontfile=',
                               fontPath,
                               ':fontsize=30:fontcolor=green:x=(w-text_w)/2:y=h/2-ascent:text=',
                               EscapeStringForFfmpeg(curCaption),
                               ', drawtext=fontfile=',
                               fontPath,
                               ':fontsize=30:fontcolor=green:x=(w-text_w)/2:y=96-ascent:text=',
                               EscapeStringForFfmpeg(soundClassName),
                               '"',
                               ' -t ', str(wavDuration),
                               ' "' + curVideoOutputFilePath + '"']

            print(' '*tabSpaceCount*2 + 'Generating video...')
            
            try:
                subprocess.check_output(''.join(curVideoCommand), stderr=subprocess.STDOUT, universal_newlines=True)

                videoOutputFiles.append(curVideoOutputFileName)
            except subprocess.CalledProcessError as e:
                print('ERROR: Unable to generate video.')
                if showErrorOutput:
                    print(e.output)

concatFilePath = outputVideoPath + '/' + 'concatFile.txt'

with open(concatFilePath, 'w') as concatFile:
    for videoPath in videoOutputFiles:
        concatFile.write('file \'' + videoPath + '\'\n') # Path is relative to location of concat file (at least in Windows)

concatCommand = [ffmpegPath, ' -y -f concat -i ', '"' + concatFilePath + '"', ' -c copy ', outputVideoName + '.mp4']

print('Concatenating video files...')

try:
    subprocess.check_output(''.join(concatCommand), stderr=subprocess.STDOUT, universal_newlines=True)
except subprocess.CalledProcessError as e:
    print('ERROR: Unable to concatenate intermediate video files.')
    if showErrorOutput:
        print(e.output)

print('Removing intermediate files...')

os.remove(concatFilePath)
for videoPath in videoOutputFiles:
    os.remove(outputVideoPath + '/' + videoPath)
for videoPath in failedVideoOutputfiles:
    os.remove(outputVideoPath + '/' + videoPath)

print('Done.')

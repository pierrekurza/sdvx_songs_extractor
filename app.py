import os
import platform
import shutil
import subprocess
from bs4 import BeautifulSoup

relativeSongFolderPath = "data/music"
relativeMusicDbPath = "data/others/music_db.xml"

# Directory to save converted music to
outputDir = "SDVX Music"

audioFormats = {
    "mp3": "MP3 V0       (verly gud bang for your disk space buck)",
    "wav": "WAV 1411kbps (only choose this if you hate .ASF format)",
    "asf": "ASF VBR      (Original, lol .s3v is just .asf but renamed)"
}

rankMap = {
    1: "NOV",
    2: "ADV",
    3: "EXH",
    # 4: "INF/GRV",
    # 5: "MXM"
}

rankSuffix = ["1n", "2a", "3e", "4i", "4g", "4h", "5m"]

VERSIONS = {
    1: "SOUND VOLTEX BOOTH",
    2: "SOUND VOLTEX II INFINITE INFECTION",
    3: "SOUND VOLTEX III GRAVITY WARS",
    4: "SOUND VOLTEX IV HEAVENLY HAVEN",
    5: "SOUND VOLTEX V VIVID WAVES",
    6: "SOUND VOLTEX EXCEED GEAR"
}

if "Windows" == platform.system():
    FFMPEG = r"ffmpeg.exe"
else:
    FFMPEG = r"/usr/bin/env ffmpeg"

OVERWRITE = False


# Credits to giltay @ stackoverflow 120656
def list_dir_fp(d):
    return [os.path.join(d, f) for f in os.listdir(d)]


# Friendly interface to use the program
def cli():
    print("Welcome to SDVX song extractor")
    # Fetch game folder path
    while True:
        game_folder = input("Insert path to SDVX folder > ")
        if os.path.exists(game_folder) and "soundvoltex.dll" in os.listdir(game_folder):
            print("OK, that path looks legit, yesssss")
            break
        else:
            print("I can't see any soundvoltex.dll here :C")
    # Fetch audio format choice
    while True:
        print("Choose your format!\n", "-" * 30)
        for i, audioFormat in audioFormats.items():
            print("%s = %s}" % (i, audioFormat))
        output_format = input("> ")
        if output_format in audioFormats.keys():
            print("OK starting...")
            break
        else:
            print("Incorrect format specified")
    return game_folder, output_format


# Gets list of all full relative paths to wanted .s3v files
def get_song_paths(game_folder):
    song_paths = []
    songs_folder = os.path.join(game_folder, relativeSongFolderPath)
    for songFolder in list_dir_fp(songs_folder):
        if os.path.isdir(songFolder):
            for filename in list_dir_fp(songFolder):
                if filename.endswith(".s3v") and not filename.endswith("_pre.s3v"):
                    song_paths.append(filename)
                elif filename.endswith(".2dx") and not filename.endswith("_pre.2dx"):
                    song_paths.append(filename)
    return song_paths


# Convert and-or copy songs and place them in music directory
def extract_songs(song_paths, output_format, metadata):
    output_folder = os.path.join(outputDir, output_format)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for name in VERSIONS.values():
        if not os.path.exists(os.path.join(output_folder, name)):
            os.makedirs(os.path.join(output_folder, name))
    # ID3v2.3
    meta_params = {
        "title": '%s',  # Title
        "artist": '%s',  # Artist
        "album_artist": "Various Artist",  # Album Artist
        "album": '%s',  # Album
        "genre": '%s',  # Genre
        "date": '%04d',  # Year
        "track": '%d',  # Track
        "disc": '%d',  # Disc (Version)
        "TBPM": '%s',  # BPM
    }
    cmd = {
        "wav": FFMPEG + ''' -y -ss 0.9 -i "%s" -i "%s" -map 0:0 -map 1:0 -id3v2_version 3''',
        "mp3": FFMPEG + ''' -y -ss 0.9 -i "%s" -i "%s" -map 0:0 -map 1:0 -id3v2_version 3 -q:a 0''',
        "asf": False
    }[output_format]

    for key, meta in meta_params.items():
        cmd += ''' -metadata:g %s="%s"''' % (key, meta)
    cmd += r' "%s"'

    for song_path in song_paths:
        filename = os.path.basename(song_path)
        song_id = filename.split("_")[0]
        if int(song_id) not in metadata:
            print("Skipping %s, because removed from music_db.xml" % song_id)
            continue
        meta = metadata[int(song_id)]
        output_file = os.path.join(output_folder, VERSIONS[meta["version"]], filename[:-3] + output_format)
        overwrite = False
        # overwrite = "&" in meta["title"] or "&" in meta["artist"]
        if (not os.path.exists(output_file)) or overwrite:
            jacket_path = get_jacket(song_path, int(song_id))

            bpm = meta["bpm_min"]
            if not bpm == meta["bpm_max"]:
                bpm = meta["bpm_max"]

            title = cmd_escape(meta["title"])
            artist = cmd_escape(meta["artist"])

            if filename.endswith(".2dx"):
                # .2dx file needs convert to wave files
                iidx_cmd = r'2dx_extract\\bin\\2dx_extract.exe "%s"' % song_path
                subprocess.run(iidx_cmd, shell=True, check=True)
                filename = filename.replace(".2dx", ".s3v")
                # rename to s3v file
                song_path = song_path.replace(".2dx", ".s3v")
                if not os.path.exists(song_path):
                    # copy extracted from .2dx wave file as .s3v
                    shutil.copy2("1.wav", song_path)
                # remove temporary files
                for wfiles in os.listdir("."):
                    if os.path.isfile(wfiles) and wfiles.endswith(".wav"):
                        os.remove(wfiles)

            exec_cmd = cmd % (
                song_path,
                jacket_path,
                title, artist,
                VERSIONS[meta["version"]], meta["genre"],
                int(meta["release_year"]),
                int(song_id), int(meta["version"]), bpm,
                output_file,
            )
            try:
                subprocess.run(exec_cmd, shell=True, check=True) \
                    if cmd else shutil.copy2(song_path, output_file)
            except subprocess.CalledProcessError as e:
                print("\n===================================\n"
                      + exec_cmd +
                      "\n===================================\n")
                print("ERROR", e.stderr)


def get_jacket(song_path, song_id):
    song_dir = os.path.dirname(song_path)
    data_dir = os.path.normpath(os.path.join(song_dir, os.path.pardir, os.path.pardir))
    file_suffix = os.path.splitext(os.path.basename(song_path))[0].split("_")[-1]
    if file_suffix in rankSuffix:
        jk_file = 'jk_{0:04d}_{1}_b.png'.format(song_id, file_suffix[0])
        jk_path = os.path.join(song_dir, jk_file)
        if os.path.exists(jk_path):
            return jk_path
    for rank in sorted(rankMap.keys(), reverse=True):
        jk_file = 'jk_{0:04d}_{1}_b.png'.format(song_id, rank)
        jk_path = os.path.join(song_dir, jk_file)
        if os.path.exists(jk_path):
            return jk_path
    return os.path.join(data_dir, "graphics", "jk_dummy_b.png")


def extract_songs_metadata(song_paths, game_folder):
    metadatum = {}
    song_ids = [int(os.path.basename(filename).split("_")[0]) for filename in song_paths]

    with open(os.path.join(game_folder, relativeMusicDbPath), "r", encoding="Shift-JIS", errors="ignore") as xmlFile:
        soup = BeautifulSoup(xmlFile.read(), "lxml")

    metas = soup.find_all("music")
    for meta in metas:
        metadatum[int(meta["id"])] = {
            "title": fix_broken_chars(meta.find("title_name").text),
            "artist": fix_broken_chars(meta.find("artist_name").text),
            "genre": meta.find("genre").text,
            # "title_sort": jaconv.h2z(meta.find("title_yomigana").text),
            # "artist_sort": jaconv.h2z(meta.find("artist_yomigana").text),
            "release_year": meta.find("distribution_date").text[:4],
            "version": int(meta.find("version").text),
            "bpm_max": (int(meta.find("bpm_max").text) / 100),
            "bpm_min": (int(meta.find("bpm_min").text) / 100),
            "volume": int(meta.find("volume").text) / 127.0,
            "track": int(meta["id"])
        }

    metadatum[9001] = {
        "title": "SOUND VOLTEX Tutorial",
        "artist": "SOUND VOLTEX Team",
        "genre": "Tutorial",
        # "title_sort": "さうんどぼるてっくすちゅーとりある",
        # "artist_sort": "さうんどぼるてっくすちーむ",
        "release_year": "2020",
        "version": 6,
        "bpm_max": 110,
        "bpm_min": 110,
        "volume": 127.0,
        "track": 9001
    }

    return metadatum


# ref: https://gist.github.com/hannahherbig/d67c2bfefcca207640c001e0ddd5e000
def fix_broken_chars(name):
    broken_chars_list = [
        # ['\u014d', '驪'],
        ['\u203E', '~'],
        ['\u301C', '～'],
        ['\u49FA', 'ê'],
        ['\u58ec', 'ê'],
        ['\u7F47', 'ê'],
        ['\u5F5C', 'ū'],
        ['\u8515', 'ῦ'],
        ['\u66E6', 'à'],
        ['\u66E9', 'è'],
        ['\u9F77', 'é'],
        ['\u745f', 'ō'],
        ['\u8E94', '🐾'],
        ['\u8d81', 'Ǣ'],
        ['\u8e59', 'ℱ'],
        ['\u91c1', '🍄'],
        ['\u994C', '²'],
        ['\u9448', '♦'],
        ['\u96cb', 'Ǜ'],
        ['\u973B', '♠'],
        ['\u983d', 'ä'],
        ['\u9A2B', 'á'],
        ['\u9A69', 'Ø'],
        ['\u7162', 'ø'],
        ['\u9A6A', 'ō'],
        ['\u9A6B', 'ā'],
        ['\u9AAD', 'ü'],
        ['\u9B2F', 'ī'],
        ['\u9EF7', 'ē'],
        ['\u9F63', 'Ú'],
        ['\u01B5', 'Ƶ'],
        ['\u95C3', 'Ā'],
        ['\u9F67', 'Ä'],
        ['\u9F6A', '♣'],
        ['\u9F72', '♥'],
        ['\u9B3B', '♃'],
        ['\u9F76', '♡'],
        ['\u9b06', 'Ý'],
        ['\u9b25', 'Ã'],
        ['\u9b2e', '¡'],
        ['\u9efb', '*'],
        ['\u9f95', '€'],
        ['\u9477', 'ゔ'],
        ['\u76E5', '⚙'],

    ]
    for m in broken_chars_list:
        name = name.replace(m[0], m[1])
    return name


def cmd_escape(string_input: str):
    if "Windows" == platform.system():
        # For PowerShell
        escape_file = [
            ['"', '\`"'],
            # ['&', '\\&'],
        ]
    else:
        # Linux
        escape_file = [
            ['"', '\"'],
            ['$', '\$']
        ]
    for repl in escape_file:
        return string_input.replace(repl[0], repl[1])


def main(argv=None):
    game_folder, output_format = cli()
    song_paths = get_song_paths(game_folder)
    print("Loading meta datum...")
    music_metadatas = extract_songs_metadata(song_paths, game_folder)
    print("Extract songs...")
    extract_songs(song_paths, output_format, music_metadatas)
    print("Finished !")


main()

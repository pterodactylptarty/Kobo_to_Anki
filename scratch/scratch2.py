import subprocess


def text_to_speech(text, voice, output_file):
    """
    Convert text to speech using a specified voice and save to an output file.

    :param text: The text to be spoken.
    :param voice: The voice to use for speech synthesis.
    :param output_file: The file path to save the audio output.
    """
    try:
        # Constructing the command to use macOS's say command
        command = f'say -v {voice} "{text}" -o {output_file}'

        # Executing the command
        subprocess.run(command, shell=True, check=True)
        print(f"Audio saved to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error in text-to-speech conversion: {e}")


# # Example usage
#italian
# text = "Ciao, come stai oggi?"
# voice = "Alice"  # Replace "Alice" with the actual name of Siri Voice 2 for Italian
# output_file = "output.aiff"  # Output file name



#german
text = "Hallo, wie gehts bei dir?"
voice = "Anna"  # Replace "Alice" with the actual name of Siri Voice 2 for Italian
output_file = "output.aiff"
text_to_speech(text, voice, output_file)

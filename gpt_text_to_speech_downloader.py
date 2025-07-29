import streamlit as st
import subprocess
import os
import shlex
import ffmpeg  # Import the ffmpeg-python library

# --- Page Configuration ---
# Set the title and a favicon for the browser tab.
st.set_page_config(page_title="cURL to MP3 Downloader", page_icon="🎵")

# --- Application UI ---
st.title("cURL Command to MP3 Downloader")
st.markdown("""
This application executes a `cURL` command, converts the resulting audio file to MP3 using `ffmpeg-python`, and offers it for download.

**How to use:**
1.  Paste your full `cURL` command into the text area below. The app handles commands copied from the Windows Command Prompt (by removing `^` characters).
2.  Enter a desired name for the output file.
3.  Click the "Generate and Download MP3" button.

The app will download the audio, convert it to `.mp3`, and provide a download link.
""")

# --- Prerequisite Warning ---
st.info("ℹ️ **Prerequisite:** This application requires **FFmpeg** to be installed on the system to handle audio conversion. The `ffmpeg-python` library is a wrapper around the FFmpeg command-line tool, so the tool itself must still be installed and accessible in your system's PATH.")


# --- Security Warning ---
# It's crucial to warn users about the potential security risks of executing arbitrary commands.
st.warning(
    "⚠️ **Security Warning:** This application executes shell commands based on your input. "
    "Only run `cURL` commands from trusted sources. Malicious commands could potentially "
    "harm your system or expose sensitive data."
)

# --- User Input Fields ---
# A larger text area is suitable for potentially long cURL commands.
curl_command_input = st.text_area(
    "Enter your cURL command here:",
    height=150,
    placeholder="curl -X POST https://api.example.com/text-to-speech ..."
)

# A standard text input for the filename.
file_name_input = st.text_input(
    "Enter the desired output filename (without extension):",
    placeholder="my_audio_file"
)

# --- Execution Logic ---
# This button triggers the main functionality of the app.
if st.button("Generate and Download MP3"):
    # --- Input Validation ---
    if not curl_command_input:
        st.error("Please enter a cURL command to execute.")
    elif not file_name_input:
        st.error("Please provide a filename for the output.")
    else:
        # --- Command Construction and Execution ---
        aac_file = None
        mp3_file_path = None
        try:
            # Use os.path.basename to prevent directory traversal attacks
            safe_filename = os.path.basename(file_name_input)
            aac_filename = f"{safe_filename}.aac"
            mp3_filename = f"{safe_filename}.mp3"

            # Clean the input command by removing Windows CMD escape characters (^).
            cleaned_command = curl_command_input.replace('^', '')

            # Use shlex.split to safely parse the cleaned command-line string
            command_list = shlex.split(cleaned_command)
            command_list.extend(["--output", aac_filename])

            st.info(f"Executing cleaned command: `{' '.join(command_list)}`")

            # Execute the cURL command
            with st.spinner(f"Downloading '{aac_filename}'..."):
                process = subprocess.run(
                    command_list,
                    capture_output=True,
                    text=True,
                    check=False
                )

            # --- cURL Process Results ---
            if process.returncode != 0:
                st.error(f"cURL command failed with exit code {process.returncode}.")
                if process.returncode == 3:
                    st.warning(
                        "**Hint: The URL in your command appears to be malformed.**\n\n"
                        "Please carefully check the URL for typos or incorrect formatting."
                    )
                st.code(f"Terminal Output (stderr):\n{process.stderr}", language="bash")
            # Check if the primary output file exists
            elif not os.path.exists(aac_filename):
                st.warning("Command executed, but the output file was not found.")
                st.info("Review the command's output below for details:")
                st.code(process.stdout or "No standard output.", language="text")
                st.code(process.stderr or "No standard error output.", language="bash")
            else:
                st.success(f"File '{aac_filename}' downloaded successfully!")
                aac_file = aac_filename # Mark for cleanup

                # --- AAC to MP3 Conversion Step using ffmpeg-python ---
                with st.spinner(f"Converting '{aac_filename}' to '{mp3_filename}'..."):
                    try:
                        # Define the input and output for ffmpeg
                        (
                            ffmpeg
                            .input(aac_filename)
                            .output(mp3_filename, audio_bitrate='192k')
                            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                        )
                        
                        st.success(f"Successfully converted to '{mp3_filename}'!")
                        mp3_file_path = mp3_filename # Mark for cleanup

                        # Read the generated MP3 file for the download button
                        with open(mp3_filename, "rb") as file:
                            st.download_button(
                                label=f"Download {mp3_filename}",
                                data=file,
                                file_name=mp3_filename,
                                mime="audio/mpeg"  # MIME type for MP3
                            )

                    except ffmpeg.Error as e:
                        st.error("FFmpeg conversion failed.")
                        st.code(f"FFmpeg Error Output (stderr):\n{e.stderr.decode('utf8')}", language="bash")
                    except FileNotFoundError:
                        st.error(
                            "Error: `ffmpeg` executable not found. "
                            "Please ensure FFmpeg is installed and accessible in your system's PATH."
                        )

        except FileNotFoundError:
            st.error(
                "Error: `curl` command not found. "
                "Please ensure cURL is installed on the system and accessible in the system's PATH."
            )
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
        finally:
            # --- Cleanup ---
            # Clean up the temporary files after the process is complete
            if aac_file and os.path.exists(aac_file):
                os.remove(aac_file)
            if mp3_file_path and os.path.exists(mp3_file_path):
                # Note: Streamlit holds the file in memory for download, 
                # so deleting it immediately is generally safe.
                os.remove(mp3_file_path)

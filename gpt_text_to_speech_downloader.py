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

# --- Deployment Prerequisite Information ---
st.info("ℹ️ **Deployment Prerequisite:** This application requires **FFmpeg** to be installed on the **server environment** where this Streamlit app is hosted. The `ffmpeg-python` library acts as a wrapper around the FFmpeg command-line tool, so the tool itself must be available on the server's PATH. Users interacting with the deployed web app will **not** need to install FFmpeg locally.")


# --- Security Warning ---
# It's crucial to warn users about the potential security risks of executing arbitrary commands.
st.warning(
    "⚠️ **Security Warning:** This application executes shell commands based on your input. "
    "Only run `cURL` commands from trusted sources. Malicious commands could potentially "
    "harm the server system or expose sensitive data."
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
        # Initialize file paths for cleanup
        aac_file = None
        mp3_file_path = None
        try:
            # Use os.path.basename to prevent directory traversal attacks
            safe_filename = os.path.basename(file_name_input)
            aac_filename = f"{safe_filename}.aac"
            mp3_filename = f"{safe_filename}.mp3"

            # Clean the input command by removing Windows CMD escape characters (^).
            # This makes the command more compatible across different shell environments.
            cleaned_command = curl_command_input.replace('^', '')

            # Use shlex.split to safely parse the cleaned command-line string into a list of arguments.
            command_list = shlex.split(cleaned_command)
            # Append the output flag and filename to the cURL command
            command_list.extend(["--output", aac_filename])

            st.info(f"Executing cleaned cURL command: `{' '.join(command_list)}`")

            # Execute the cURL command to download the audio file.
            # capture_output=True: captures stdout and stderr.
            # text=True: decodes stdout/stderr as text.
            # check=False: prevents subprocess.run from raising an exception for non-zero exit codes,
            # allowing manual error handling.
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
                # Display standard error output from cURL for debugging
                st.code(f"Terminal Output (stderr):\n{process.stderr}", language="bash")
            # Check if the primary output file exists after cURL execution
            elif not os.path.exists(aac_filename):
                st.warning("Command executed, but the output file was not found.")
                st.info("Review the command's output below for details:")
                st.code(process.stdout or "No standard output.", language="text")
                st.code(process.stderr or "No standard error output.", language="bash")
            else:
                st.success(f"File '{aac_filename}' downloaded successfully!")
                aac_file = aac_filename # Mark for cleanup in finally block

                # --- Verify AAC file integrity before conversion ---
                with st.spinner(f"Verifying '{aac_filename}'..."):
                    try:
                        probe_result = ffmpeg.probe(aac_filename)
                        if not probe_result.get('streams'):
                            st.error(f"Error: '{aac_filename}' appears to be an empty or invalid audio file (no streams detected).")
                            st.info("Please check your cURL command and the source of the audio.")
                            # Do not proceed with conversion if file is invalid
                            return
                        else:
                            st.info(f"'{aac_filename}' verified successfully. Proceeding with conversion.")
                    except ffmpeg.Error as e:
                        st.error(f"Error probing '{aac_filename}'. It might be corrupted or not a valid AAC file.")
                        st.code(f"FFprobe Error Output (stderr):\n{e.stderr.decode('utf8')}", language="bash")
                        # Do not proceed with conversion if probe fails
                        return
                    except Exception as e:
                        st.error(f"An unexpected error occurred during file verification: {e}")
                        return

                # --- AAC to MP3 Conversion Step using ffmpeg-python ---
                with st.spinner(f"Converting '{aac_filename}' to '{mp3_filename}'..."):
                    try:
                        # Define the input and output for ffmpeg.
                        # audio_bitrate='192k': sets the output MP3 bitrate to 192 kbps.
                        # run(): executes the ffmpeg command.
                        # capture_stdout/stderr: captures ffmpeg's output for debugging.
                        # overwrite_output=True: allows ffmpeg to overwrite an existing output file.
                        (
                            ffmpeg
                            .input(aac_filename)
                            .output(mp3_filename, audio_bitrate='192k')
                            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                        )
                        
                        st.success(f"Successfully converted to '{mp3_filename}'!")
                        mp3_file_path = mp3_filename # Mark for cleanup

                        # Read the generated MP3 file in binary mode for the download button
                        with open(mp3_filename, "rb") as file:
                            st.download_button(
                                label=f"Download {mp3_filename}",
                                data=file,
                                file_name=mp3_filename,
                                mime="audio/mpeg"  # Correct MIME type for MP3 audio
                            )

                    except ffmpeg.Error as e:
                        # Catch specific ffmpeg errors and display them
                        st.error("FFmpeg conversion failed.")
                        st.code(f"FFmpeg Error Output (stderr):\n{e.stderr.decode('utf8')}", language="bash")
                    except Exception as e:
                        # Catch any other unexpected errors during ffmpeg conversion
                        st.error(f"An unexpected error occurred during conversion: {e}")

        except Exception as e:
            # Catch any other unexpected errors during the overall process (e.g., cURL execution)
            st.error(f"An unexpected error occurred: {e}")
        finally:
            # --- Cleanup ---
            # Ensure temporary files are removed regardless of success or failure
            if aac_file and os.path.exists(aac_file):
                try:
                    os.remove(aac_file)
                    st.info(f"Cleaned up temporary file: '{aac_file}'")
                except OSError as e:
                    st.warning(f"Could not remove temporary file '{aac_file}': {e}")
            if mp3_file_path and os.path.exists(mp3_file_path):
                try:
                    # Note: Streamlit holds the file in memory for download, 
                    # so deleting it immediately after the download button is displayed is generally safe.
                    os.remove(mp3_file_path)
                    st.info(f"Cleaned up temporary file: '{mp3_file_path}'")
                except OSError as e:
                    st.warning(f"Could not remove temporary file '{mp3_file_path}': {e}")


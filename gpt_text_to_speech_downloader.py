import streamlit as st
import subprocess
import os
import shlex

# --- Page Configuration ---
# Set the title and a favicon for the browser tab.
st.set_page_config(page_title="GPT tex to speech audio Downloader", page_icon="⬇️")

# --- Application UI ---
st.title("GPT text to speech Downloader")
st.markdown("""
This application provides a user-friendly interface to execute a `cURL` command and download the resulting output file.

**How to use:**
1.  Paste your full `cURL` command into the text area below. The app will automatically handle commands copied from the Windows Command Prompt (by removing `^` characters).
2.  Enter a desired name for the output file (the `.aac` extension will be added automatically).
3.  Click the "Generate and Download File" button.

The app will then execute the command and, if successful, provide a button to download your file.
""")

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
if st.button("Generate and Download File"):
    # --- Input Validation ---
    if not curl_command_input:
        st.error("Please enter a cURL command to execute.")
    elif not file_name_input:
        st.error("Please provide a filename for the output.")
    else:
        # --- Command Construction and Execution ---
        try:
            # Use os.path.basename to prevent directory traversal attacks (e.g., ../../etc/passwd)
            safe_filename = os.path.basename(file_name_input)
            output_filename = f"{safe_filename}.aac"

            # Clean the input command by removing Windows CMD escape characters (^).
            cleaned_command = curl_command_input.replace('^', '')

            # Use shlex.split to safely parse the cleaned command-line string into a list of arguments.
            # This is a security best practice over using shell=True.
            command_list = shlex.split(cleaned_command)
            command_list.extend(["--output", output_filename])

            st.info(f"Executing cleaned command: `{' '.join(command_list)}`")

            # Show a spinner to indicate that the process is running in the background.
            with st.spinner(f"Executing command and generating '{output_filename}'..."):
                # Execute the command using subprocess.run.
                # We set check=False to manually handle errors and inspect the output.
                process = subprocess.run(
                    command_list,
                    capture_output=True,
                    text=True,
                    check=False
                )

            # --- Process Results ---
            # A return code of 0 typically indicates success.
            if process.returncode == 0:
                # After the command runs, verify that the output file was actually created.
                if os.path.exists(output_filename):
                    st.success(f"File '{output_filename}' generated successfully!")

                    # Read the generated file in binary mode for the download button.
                    with open(output_filename, "rb") as file:
                        st.download_button(
                            label=f"Download {output_filename}",
                            data=file,
                            file_name=output_filename,
                            mime="audio/aac"  # Set the appropriate MIME type for the file.
                        )
                else:
                    # Handle cases where the command runs but doesn't produce the expected file.
                    st.warning("Command executed, but the output file was not found.")
                    st.info("Review the command's output below for details:")
                    st.code(process.stdout or "No standard output.", language="text")
                    st.code(process.stderr or "No standard error output.", language="bash")
            else:
                # If the command fails, show the error message from stderr.
                st.error(f"Command failed with exit code {process.returncode}.")

                # Provide specific help for common curl errors, like code 3 (CURLE_URL_MALFORMAT).
                if process.returncode == 3:
                    st.warning(
                        "**Hint: The URL in your command appears to be malformed.**\n\n"
                        "This error often means the URL was not entered correctly. "
                        "Please carefully check the URL in your command for common issues like:\n"
                        "* Typos or extra spaces within the URL.\n"
                        "* An invalid port number (e.g., `hostname:port`).\n"
                        "* Missing or incorrect protocol (e.g., `http://` or `https://`)."
                    )
                
                # Display the actual error output from the command.
                st.code(f"Terminal Output (stderr):\n{process.stderr}", language="bash")

        except FileNotFoundError:
            st.error(
                "Error: `curl` command not found. "
                "Please ensure cURL is installed on the system and accessible in the system's PATH."
            )
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

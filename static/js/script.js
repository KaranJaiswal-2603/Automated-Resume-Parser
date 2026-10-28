
document.addEventListener("DOMContentLoaded", function () {
    const resumeInput = document.getElementById("resume");
    const fileNameDisplay = document.getElementById("file-name");
    const errorMessage = document.getElementById("error-message");
    const resumeForm = document.getElementById("resume-form");

    const allowedExtensions = ["pdf", "docx"];
    const maxFileSize = 10 * 1024 * 1024;

    if (resumeInput && fileNameDisplay && errorMessage && resumeForm) {
        resumeInput.addEventListener("change", function () {
            errorMessage.textContent = "";

            const file = resumeInput.files[0];

            if (!file) {
                fileNameDisplay.textContent = "Choose a PDF or DOCX file";
                return;
            }

            fileNameDisplay.textContent = file.name;

            const extension = file.name.split(".").pop().toLowerCase();

            if (!allowedExtensions.includes(extension)) {
                errorMessage.textContent = "Please select a PDF or DOCX file.";
                resumeInput.value = "";
                fileNameDisplay.textContent = "Choose a PDF or DOCX file";
                return;
            }

            if (file.size > maxFileSize) {
                errorMessage.textContent = "The file must not exceed 10 MB.";
                resumeInput.value = "";
                fileNameDisplay.textContent = "Choose a PDF or DOCX file";
            }
        });

        resumeForm.addEventListener("submit", function (event) {
            errorMessage.textContent = "";

            const file = resumeInput.files[0];

            if (!file) {
                event.preventDefault();
                errorMessage.textContent = "Please select a resume.";
                return;
            }

            const extension = file.name.split(".").pop().toLowerCase();

            if (!allowedExtensions.includes(extension)) {
                event.preventDefault();
                errorMessage.textContent = "Only PDF and DOCX files are supported.";
                return;
            }

            if (file.size > maxFileSize) {
                event.preventDefault();
                errorMessage.textContent = "The file must not exceed 10 MB.";
            }
        });
    }
});

const express = require("express");
const fs = require("fs");
const path = require("path");
const archiver = require("archiver");

const app = express();
const PORT = 3000;

// Serve static files from the public folder
app.use(express.static("public"));

// Stores List
const stores = [
    { id: 59, name: "DriveX BTM Layout" },
    { id: 446, name: "DriveX Nayana Store" },
    { id: 786, name: "DriveX Office" }
];

// Read version number from version.txt
const versionFilePath = path.join(__dirname, "veronica", "version.txt");
let version = "Unknown";

if (fs.existsSync(versionFilePath)) {
    version = fs.readFileSync(versionFilePath, "utf8").trim();
}

// Endpoint to get version
app.get("/version", (req, res) => {
    res.json({ version });
});

// Endpoint to get store list
app.get("/stores", (req, res) => {
    res.json(stores);
});

// Function to update STORE_ID while keeping other .env data intact
function updateEnvFile(envFilePath, newStoreId) {
    if (!fs.existsSync(envFilePath)) return;

    // Read existing .env content
    let envData = fs.readFileSync(envFilePath, "utf8").split("\n");

    // Update STORE_ID while keeping other values unchanged
    let updatedEnvData = envData.map(line => {
        return line.startsWith("STORE_ID=") ? `STORE_ID=${newStoreId}` : line;
    });

    // Write updated data back to .env
    fs.writeFileSync(envFilePath, updatedEnvData.join("\n"));
}

// Route to generate ZIP with selected store_id
app.get("/download/:storeId", (req, res) => {
    const storeId = req.params.storeId;
    const folderToZip = path.join(__dirname, "veronica");
    const envFilePath = path.join(folderToZip, ".env");
    const zipFileName = `veronica.zip`;
    const zipFilePath = path.join(__dirname, zipFileName);

    // Check if the folder exists
    if (!fs.existsSync(folderToZip)) {
        return res.status(404).send("Folder not found.");
    }

    // Validate store ID
    const selectedStore = stores.find(store => store.id == storeId);
    if (!selectedStore) {
        return res.status(400).send("Invalid store ID.");
    }

    // Update only STORE_ID in .env
    updateEnvFile(envFilePath, storeId);

    // Create ZIP archive
    const output = fs.createWriteStream(zipFilePath);
    const archive = archiver("zip", { zlib: { level: 9 } });

    output.on("close", () => {
        console.log(`ZIP file created: ${archive.pointer()} bytes`);

        // Send the ZIP file to the user
        res.download(zipFilePath, zipFileName, (err) => {
            if (err) {
                console.error("Download error:", err);
            } else {
                console.log(`ZIP file ${zipFilePath} sent successfully.`);

                // Delete the ZIP file after sending
                fs.unlink(zipFilePath, (unlinkErr) => {
                    if (unlinkErr) {
                        console.error(`Error deleting ZIP file: ${unlinkErr}`);
                    } else {
                        console.log(`Deleted ZIP file: ${zipFilePath}`);
                    }
                });
            }
        });
    });

    archive.on("error", (err) => {
        console.error("ZIP archive error:", err);
        res.status(500).send("Error creating ZIP file.");
    });

    archive.pipe(output);
    archive.directory(folderToZip, false);
    archive.finalize();
});

// Start server
app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running at http://localhost:${PORT}`);
});

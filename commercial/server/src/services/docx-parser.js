import mammoth from "mammoth";
import fs from "fs";
import path from "path";

/**
 * Parse a DOCX file and extract text + embedded images.
 * Returns { text, images: [{ path, contentType }] }
 */
export async function parseDocx(filePath, outputDir) {
  const buffer = fs.readFileSync(filePath);

  // Ensure output dir for images
  const imagesDir = path.join(outputDir, "docx_images");
  fs.mkdirSync(imagesDir, { recursive: true });

  let imageIndex = 0;
  const extractedImages = [];

  const result = await mammoth.convertToMarkdown(buffer, {
    convertImage: mammoth.images.imgElement((image) => {
      imageIndex++;
      const ext = image.contentType === "image/png" ? "png" : "jpg";
      const imgPath = path.join(imagesDir, `docx_img_${imageIndex}.${ext}`);

      return image.read().then((imgBuffer) => {
        fs.writeFileSync(imgPath, imgBuffer);
        extractedImages.push({
          path: imgPath,
          contentType: image.contentType,
          fileName: `docx_img_${imageIndex}.${ext}`,
        });
        return { src: imgPath };
      });
    }),
  });

  // Clean up the markdown text (remove image references since we extracted them)
  const text = result.value
    .replace(/!\[.*?\]\(.*?\)/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return {
    text,
    images: extractedImages,
    hasImages: extractedImages.length > 0,
  };
}

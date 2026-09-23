# from pathlib import Path

# import cv2


# class ImagePreprocessor:

#     def __init__(self, output_dir="output/preprocessed"):
#         self.output_dir = Path(output_dir)

#         self.output_dir.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#     def preprocess(self, image_path, page_number):

#         image_path = Path(image_path)

#         if not image_path.exists():
#             raise FileNotFoundError(
#                 f"Image not found: {image_path}"
#             )

#         image = cv2.imread(str(image_path))

#         if image is None:
#             raise ValueError(
#                 f"Could not read image: {image_path}"
#             )

#         # Convert to grayscale
#         gray = cv2.cvtColor(
#             image,
#             cv2.COLOR_BGR2GRAY
#         )

#         # Improve local contrast
#         clahe = cv2.createCLAHE(
#             clipLimit=2.0,
#             tileGridSize=(8, 8)
#         )

#         enhanced = clahe.apply(gray)

#         # Mild denoising
#         denoised = cv2.fastNlMeansDenoising(
#             enhanced,
#             None,
#             10,
#             7,
#             21
#         )

#         # Adaptive threshold
#         thresholded = cv2.adaptiveThreshold(
#             denoised,
#             255,
#             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY,
#             31,
#             11
#         )

#         # Save variants
#         output_paths = {}

#         original_path = (
#             self.output_dir /
#             f"page_{page_number:03d}_original.png"
#         )

#         enhanced_path = (
#             self.output_dir /
#             f"page_{page_number:03d}_enhanced.png"
#         )

#         thresholded_path = (
#             self.output_dir /
#             f"page_{page_number:03d}_threshold.png"
#         )

#         cv2.imwrite(
#             str(original_path),
#             image
#         )

#         cv2.imwrite(
#             str(enhanced_path),
#             denoised
#         )

#         cv2.imwrite(
#             str(thresholded_path),
#             thresholded
#         )

#         output_paths["original"] = str(original_path)
#         output_paths["enhanced"] = str(enhanced_path)
#         output_paths["threshold"] = str(thresholded_path)

#         return output_paths



























from pathlib import Path

import cv2


class ImagePreprocessor:

    # =========================================================
    # SURYA PERFORMANCE SETTING
    # =========================================================
    #
    # The 300-DPI source image is preserved.
    #
    # Only the copies sent to Surya are resized.
    #
    # 2000 px is intentionally conservative:
    # - keeps small multilingual text readable
    # - reduces Surya inference workload
    # - stays below Surya's documented ~2048 px guidance
    #
    SURYA_MAX_WIDTH = 2000

    def __init__(self, output_dir="output/preprocessed"):
        self.output_dir = Path(output_dir)

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # =========================================================
    # SURYA RESIZE HELPER
    # =========================================================

    def _create_surya_image(
        self,
        image,
        output_path
    ):
        """
        Create a high-quality reduced-resolution image
        specifically for Surya.

        IMPORTANT:
        The original high-resolution image is never modified.
        """

        height, width = image.shape[:2]

        # -----------------------------------------------------
        # No resize required
        # -----------------------------------------------------

        if width <= self.SURYA_MAX_WIDTH:

            cv2.imwrite(
                str(output_path),
                image
            )

            return

        # -----------------------------------------------------
        # Preserve aspect ratio
        # -----------------------------------------------------

        scale = (
            self.SURYA_MAX_WIDTH
            / float(width)
        )

        new_width = int(
            width * scale
        )

        new_height = int(
            height * scale
        )

        resized = cv2.resize(
            image,
            (
                new_width,
                new_height
            ),
            interpolation=cv2.INTER_AREA
        )

        cv2.imwrite(
            str(output_path),
            resized
        )

    # =========================================================
    # PREPROCESS
    # =========================================================

    def preprocess(
        self,
        image_path,
        page_number
    ):

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        # =====================================================
        # LOAD ORIGINAL
        # =====================================================

        image = cv2.imread(
            str(image_path)
        )

        if image is None:
            raise ValueError(
                f"Could not read image: {image_path}"
            )

        height, width = image.shape[:2]

        print(
            f"Input image size : "
            f"{width}x{height}"
        )

        # =====================================================
        # FULL-RESOLUTION ORIGINAL
        # =====================================================

        original_path = (
            self.output_dir
            / f"page_{page_number:03d}_original.png"
        )

        cv2.imwrite(
            str(original_path),
            image
        )

        # =====================================================
        # GRAYSCALE
        # =====================================================

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # =====================================================
        # CLAHE
        # =====================================================

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        enhanced = clahe.apply(
            gray
        )

        # =====================================================
        # MILD DENOISING
        # =====================================================

        denoised = cv2.fastNlMeansDenoising(
            enhanced,
            None,
            10,
            7,
            21
        )

        # =====================================================
        # ADAPTIVE THRESHOLD
        # =====================================================

        thresholded = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11
        )

        # =====================================================
        # FULL-RES ENHANCED
        # =====================================================

        enhanced_path = (
            self.output_dir
            / f"page_{page_number:03d}_enhanced.png"
        )

        cv2.imwrite(
            str(enhanced_path),
            denoised
        )

        # =====================================================
        # FULL-RES THRESHOLD
        # =====================================================

        thresholded_path = (
            self.output_dir
            / f"page_{page_number:03d}_threshold.png"
        )

        cv2.imwrite(
            str(thresholded_path),
            thresholded
        )

        # =====================================================
        # SURYA ORIGINAL
        # =====================================================

        surya_original_path = (
            self.output_dir
            / f"page_{page_number:03d}_surya_original.png"
        )

        self._create_surya_image(
            image,
            surya_original_path
        )

        # =====================================================
        # SURYA ENHANCED
        # =====================================================

        surya_enhanced_path = (
            self.output_dir
            / f"page_{page_number:03d}_surya_enhanced.png"
        )

        self._create_surya_image(
            denoised,
            surya_enhanced_path
        )

        # =====================================================
        # SURYA THRESHOLD
        # =====================================================

        surya_threshold_path = (
            self.output_dir
            / f"page_{page_number:03d}_surya_threshold.png"
        )

        self._create_surya_image(
            thresholded,
            surya_threshold_path
        )

        # =====================================================
        # PRINT SURYA SIZE
        # =====================================================

        surya_image = cv2.imread(
            str(surya_original_path)
        )

        if surya_image is not None:

            surya_height, surya_width = (
                surya_image.shape[:2]
            )

            print(
                f"Surya image size : "
                f"{surya_width}x{surya_height}"
            )

            reduction = (
                1.0
                - (
                    surya_width
                    * surya_height
                )
                / (
                    width
                    * height
                )
            ) * 100

            print(
                f"Surya pixel reduction : "
                f"{reduction:.1f}%"
            )

        # =====================================================
        # RETURN ALL PATHS
        # =====================================================

        return {

            # -------------------------------------------------
            # Full-resolution images
            # -------------------------------------------------

            "original": str(
                original_path
            ),

            "enhanced": str(
                enhanced_path
            ),

            "threshold": str(
                thresholded_path
            ),

            # -------------------------------------------------
            # Surya-optimized images
            # -------------------------------------------------

            "surya_original": str(
                surya_original_path
            ),

            "surya_enhanced": str(
                surya_enhanced_path
            ),

            "surya_threshold": str(
                surya_threshold_path
            ),
        }
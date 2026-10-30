
import bpy
import os
from array import array

from ..gtaLib import txd


#######################################################
class DFFSceneTXDExtractProps(bpy.types.PropertyGroup):

    input_directory: bpy.props.StringProperty(
        name="TXD Folder",
        description="Folder containing TXD files",
        subtype='DIR_PATH'
    )

    output_directory: bpy.props.StringProperty(
        name="Output Folder",
        description="Folder where extracted PNG files will be saved",
        subtype='DIR_PATH'
    )


#######################################################
class DFF_OT_txd_extract(bpy.types.Operator):

    bl_idname = "scene.dff_txd_extract"
    bl_label = "Extract All Textures"
    bl_description = "Extract all textures from TXD files into PNG images"

    def execute(self, context):

        settings = context.scene.dff_txd_extract

        input_directory = bpy.path.abspath(settings.input_directory)
        output_directory = bpy.path.abspath(settings.output_directory)

        if not os.path.isdir(input_directory):
            self.report({'ERROR'}, "Invalid TXD folder")
            return {'CANCELLED'}

        if not output_directory:
            self.report({'ERROR'}, "Select an output folder")
            return {'CANCELLED'}

        try:
            total = txd_extractor.extract_folder(
                input_directory,
                output_directory
            )

            self.report(
                {'INFO'},
                f"Extraction completed: {total} textures"
            )

        except Exception as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}

        return {'FINISHED'}


#######################################################
class DFF_PT_txd_extract(bpy.types.Panel):

    bl_label = "DragonFF - TXD Extract"
    bl_idname = "SCENE_PT_dff_txd_extract"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):

        layout = self.layout
        settings = context.scene.dff_txd_extract

        col = layout.column(align=True)

        col.prop(settings, "input_directory")
        col.prop(settings, "output_directory")

        layout.separator()

        layout.operator(
            DFF_OT_txd_extract.bl_idname,
            icon='EXPORT'
        )


#######################################################
class txd_extractor:

    input_directory = ""
    output_directory = ""

    #######################################################
    @staticmethod
    def get_unique_path(name):

        self = txd_extractor

        name = bpy.path.clean_name(name) or "texture"

        path = os.path.join(self.output_directory, f"{name}.png")

        index = 1

        while os.path.exists(path):
            path = os.path.join(
                self.output_directory,
                f"{name}_{index}.png"
            )
            index += 1

        return path

    #######################################################
    @staticmethod
    def save_image(name, width, height, rgba):

        self = txd_extractor

        image = bpy.data.images.new(
            name=name,
            width=width,
            height=height,
            alpha=True
        )

        try:
            pixels = array('f', (value / 255.0 for value in rgba))
            image.pixels.foreach_set(pixels)

            image.filepath_raw = self.get_unique_path(name)
            image.file_format = 'PNG'
            image.save()

        finally:
            bpy.data.images.remove(image)

    #######################################################
    @staticmethod
    def extract_texture(texture):

        rgba = texture.to_rgba()

        if rgba is None:
            raise RuntimeError("Unsupported texture format")

        txd_extractor.save_image(
            texture.name,
            texture.width,
            texture.height,
            rgba
        )

    #######################################################
    @staticmethod
    def extract_file(file_path):

        dictionary = txd.txd()
        dictionary.load_file(file_path)

        extracted = 0

        for texture in dictionary.native_textures:
            try:
                txd_extractor.extract_texture(texture)
                extracted += 1
                print(f"Extracted: {texture.name}")

            except Exception as error:
                print(f"Failed: {texture.name} - {error}")

        for images, texture in zip(
            dictionary.images,
            dictionary.textures
        ):
            try:
                if not images:
                    continue

                image = images[0]
                rgba = image.to_rgba()

                if rgba is None:
                    raise RuntimeError("Unsupported image format")

                txd_extractor.save_image(
                    texture.name,
                    image.width,
                    image.height,
                    rgba
                )

                extracted += 1
                print(f"Extracted: {texture.name}")

            except Exception as error:
                print(f"Failed: {texture.name} - {error}")

        return extracted

    #######################################################
    @staticmethod
    def extract_folder(input_directory, output_directory):

        self = txd_extractor

        self.input_directory = input_directory
        self.output_directory = output_directory

        os.makedirs(output_directory, exist_ok=True)

        files = [
            os.path.join(input_directory, filename)
            for filename in os.listdir(input_directory)
            if filename.lower().endswith(".txd")
        ]

        total = 0

        print(f"Found {len(files)} TXD files")

        for file_path in files:
            try:
                print(f"\nReading: {file_path}")
                total += self.extract_file(file_path)

            except Exception as error:
                print(f"Failed to read {file_path}: {error}")

        print(f"\nExtraction completed: {total} textures")

        return total

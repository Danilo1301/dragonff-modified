# GTA DragonFF - Blender scripts to edit basic GTA formats
# Copyright (C) 2019  Parik

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import bpy
import os
from PIL import Image as PILImage
import random

from ..gtaLib import txd

#######################################################
class txd_importer:

    skip_mipmaps = True
    pack = True

    __slots__ = [
        'txd',
        'images',
        'file_name'
    ]

    #######################################################
    def _init():
        self = txd_importer

        # Variables
        self.txd = None
        self.images = {}
        self.file_name = ""

    #######################################################
    def _create_image(name, rgba, width, height, pack=False):
        print("\n========== TEXTURE DEBUG ==========")
        print("Name:", name)
        print("Size:", width, "x", height)
        print("RGBA length:", len(rgba))

        if rgba:
            print("First 32 bytes:", list(rgba[:32]))
            print("Min:", min(rgba))
            print("Max:", max(rgba))

            # Verifica se todos os bytes são zero
            all_zero = all(b == 0 for b in rgba)
            print("ALL ZERO:", all_zero)

            # Quantos pixels possuem algum valor diferente de zero
            non_zero = sum(1 for b in rgba if b != 0)
            print("Non-zero bytes:", non_zero, "/", len(rgba))

        print("==================================\n")

        pixels = []

        for h in range(height - 1, -1, -1):
            offset = h * width * 4

            pixels += list(map(
                lambda b: b / 0xff,
                rgba[offset:offset + width * 4]
            ))

        image = bpy.data.images.new(
            name,
            width,
            height,
            alpha=True
        )

        image.pixels = pixels

        # ==================================================
        # SALVAR PNG COM PIL
        # ==================================================

        if not bpy.data.filepath:
            print("[ERRO] O .blend ainda não foi salvo!")
            return image

        texture_dir = os.path.join(
            os.path.dirname(bpy.data.filepath),
            "Textures"
        )

        os.makedirs(texture_dir, exist_ok=True)

        # Mantém o nome original da imagem.
        # Apenas transforma / e \ em _
        # para formar um nome de arquivo válido.

        safe_name = name.replace("/", "_")
        safe_name = safe_name.replace("\\", "_")

        save_path = os.path.abspath(
            os.path.join(
                texture_dir,
                safe_name + ".png"
            )
        )

        print("=== SALVANDO TEXTURA COM PIL ===")
        print("Image name:", name)
        print("Save path:", save_path)

        try:
            # Os bytes RGBA vindos do TXD
            # já são exatamente o que queremos salvar.
            png = PILImage.frombytes(
                "RGBA",
                (width, height),
                bytes(rgba)
            )

            # O código original do DragonFF inverte
            # verticalmente os pixels antes de colocar
            # na imagem do Blender.
            png = png.transpose(PILImage.FLIP_TOP_BOTTOM)

            png.save(
                save_path,
                "PNG"
            )

            print("[OK] PNG salva com PIL")
            print("Existe:", os.path.exists(save_path))

        except Exception as e:
            print("[ERRO] PIL:", repr(e))

        # IMPORTANTE:
        # Continua retornando a imagem original do Blender.
        # Não remove nem recarrega.
        return image

    #######################################################
    def import_textures():
        self = txd_importer

        txd_name = os.path.basename(self.file_name).lower()

        # Import native textures
        for tex in self.txd.native_textures:
            images = []
            num_levels = tex.num_levels if not self.skip_mipmaps else 1

            for level in range(num_levels):
                image_name = "%s/%s/%d" % (txd_name, tex.name, level)

                image = bpy.data.images.get(image_name)

                if image:
                    print("========== CACHE HIT ==========")
                    print("Image:", image_name)
                    print("Path:", image.filepath)
                    print("Size:", image.size[:])

                    width = image.size[0]
                    height = image.size[1]

                    # -----------------------------------------
                    # Verifica alguns pixels aleatórios
                    # -----------------------------------------

                    is_black = False

                    if width > 0 and height > 0:
                        pixels = image.pixels

                        for i in range(8):
                            x = random.randrange(width)
                            y = random.randrange(height)

                            index = (y * width + x) * 4

                            r = pixels[index]
                            g = pixels[index + 1]
                            b = pixels[index + 2]

                            print(
                                "Pixel:",
                                x, y,
                                "RGB:",
                                r, g, b
                            )

                            # Se encontrar um pixel com cor,
                            # consideramos a textura válida.
                            if r > 0.01 or g > 0.01 or b > 0.01:
                                is_black = False
                                break

                            is_black = True

                    # -----------------------------------------
                    # CACHE ESTÁ PRETO
                    # -----------------------------------------

                    if is_black:
                        print("========== BLACK CACHE ==========")
                        print("Removing:", image_name)

                        bpy.data.images.remove(image)
                        image = None

                    else:
                        print("========== CACHE VALID ==========")

                # -----------------------------------------
                # CACHE MISS / CACHE PRETO
                # -----------------------------------------

                if not image:
                    print("========== RECREATING ==========")
                    print("Image:", image_name)

                    image = txd_importer._create_image(
                        image_name,
                        tex.to_rgba(level),
                        tex.get_width(level),
                        tex.get_height(level),
                        self.pack
                    )

                images.append(image)

            self.images[tex.name] = images

        # Import textures
        for tex, imgs in zip(self.txd.textures, self.txd.images):
            images = []
            num_levels = len(imgs) if not self.skip_mipmaps else 1

            for level in range(num_levels):
                img = imgs[level]
                image_name = "%s/%s/%d" % (txd_name, tex.name, level)
                image = txd_importer._create_image(image_name,
                                                    img.to_rgba(),
                                                    img.width,
                                                    img.height,
                                                    self.pack)
                images.append(image)

            self.images[tex.name] = images

    #######################################################
    def import_txd(file_name):
        self = txd_importer
        self._init()

        self.txd = txd.txd()
        self.txd.load_file(file_name)
        self.file_name = file_name

        self.import_textures()

#######################################################
def import_txd(options):

    txd_importer.skip_mipmaps = options['skip_mipmaps']
    txd_importer.pack = options['pack']

    txd_importer.import_txd(options['file_name'])

    return txd_importer

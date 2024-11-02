# The license for this file is
# The MIT License (MIT)
#
# Copyright (c) 2013 Andrew Duncan
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.



import logging
import pygame
import subprocess
import os
import signal

logger = logging.getLogger('l_default')



class Draw:
    """This class manages everything non-video draw elements"""
    def __init__(self, resolution, disable_pygame, name, xdisplay_id, x_offset, y_offset):
        self.resolution_width=int(resolution[0])
        self.resolution_height=int(resolution[1])
        self.name=name
        self.disable_pygame=disable_pygame
        self.xdisplay_id=xdisplay_id
        os.environ["DISPLAY"] = self.xdisplay_id
        os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x_offset},{y_offset}'

        if self.disable_pygame:
            logger.debug(
                f"Draw: {self.name} draw.init we are instructed to disable pygame, no status backgrounds will be drawn")

        else:
            pygame.init()
            self.surface = pygame.display.set_mode((self.resolution_width, self.resolution_height),pygame.NOFRAME)
            pygame.mouse.set_visible(False)

        logger.debug(
            f"Draw: {self.name} draw.init finished on DISPLAY {self.xdisplay_id}")

    def placeholder(self,absposx,absposy,width,height,background_img_path):
        """This function creates a new placeholder"""
        if self.disable_pygame:
            logger.debug(f"Draw: {self.name} Refuse to create placeholder with coordinates: {absposx}, {absposy} and width: {width} height: {height} with image {background_img_path} since we do not have a pygame surface to draw on" )
            return None
        else:
            logger.debug(f"Draw: {self.name} Drawing placeholder with coordinates: {absposx}, {absposy} and width: {width} height: {height} with image {background_img_path}" )
            background_img = pygame.image.load(background_img_path)
            background_img = pygame.transform.scale(background_img, (width, height))
            self.surface.blit(background_img, (absposx, absposy))
            self.refresh()
            return background_img


    def blank(self):
        logger.debug(
            f"Draw: {self.name} draw.blank we are instructed to blank the background")
        self.surface.fill((0, 0, 0))
        pygame.display.flip()
    def check_input(self):
        if not self.disable_pygame:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_q or event.key == pygame.K_a or event.key == pygame.K_KP_DIVIDE or event.key == pygame.K_BACKSPACE:
                            logger.debug(f"Draw: {self.name} Keypress 'a' or 'q' or 'backspace' or 'keypad /' detected.")
                            return "end_event"
                        if event.key == pygame.K_n or event.key == pygame.K_SPACE or event.key == pygame.K_KP_PLUS:
                            logger.debug(f"Draw: {self.name} Keypress 'n' or 'space' or 'keypad +' detected.")
                            return "next_event"
                        if event.key == pygame.K_r or event.key == pygame.K_KP_PERIOD or event.key == pygame.K_COMMA:
                            logger.debug(f"Draw: {self.name} Keypress 'r' or ',' or 'keypad .' detected")
                            return "resume_rotation"
                        if event.key == pygame.K_p or event.key == pygame.K_KP_MULTIPLY:
                            logger.debug(f"Draw: {self.name} Keypress 'p' or 'keypad *' detected")
                            return "pause_rotation"
                        for numeric_key_counter, key in enumerate([pygame.K_F1,pygame.K_F2,pygame.K_F3,pygame.K_F4,pygame.K_F5,pygame.K_F6,pygame.K_F7,pygame.K_F8,pygame.K_F9,pygame.K_F10,pygame.K_F11,pygame.K_F12]):
                            if event.key == key:
                                logger.debug(f"Draw: {self.name} Keypress 'F" + str(numeric_key_counter + 1) + "' detected")
                                return numeric_key_counter
                        for numeric_key_counter, key in enumerate([pygame.K_KP0,pygame.K_KP1,pygame.K_KP2,pygame.K_KP3,pygame.K_KP4,pygame.K_KP5,pygame.K_KP6,pygame.K_KP7,pygame.K_KP8,pygame.K_KP9]):
                            if event.key == key:
                                logger.debug(f"Draw: {self.name} Keypress 'keypad " + str(numeric_key_counter + 1) + "' detected")
                                return numeric_key_counter
                        else:
                            logger.debug(f"Draw: {self.name} Keypress {event.type} detected, but no action defined for this key")
                            return None
            except pygame.error as e:
                logger.debug(f"{self.name} draw: Exception " + repr(e))
                exit(0)
        else:
            logger.debug(
                f"Draw: {self.name} pygame is disabled so this instance will not check input")
    def refresh(self):
        if not self.disable_pygame:
            pygame.display.flip()

    def destroy(self):
        if not self.disable_pygame:
            logger.debug(f"Draw: {self.name} destroy")
            pygame.quit()


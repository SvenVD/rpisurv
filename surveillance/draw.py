import logging
import pygame
from setuplogging import setup_logging

logger = logging.getLogger('l_default')

def init(resolution):
    resolution_width=int(resolution[0])
    resolution_height=int(resolution[1])
    pygame.init()
    surface = pygame.display.set_mode((resolution_width, resolution_height))
    pygame.mouse.set_visible(False)
    return surface


def placeholder(absposx,absposy,width,height,background_img_path,surface):
    """This function creates a new placeholder"""
    logger.debug("Drawing placeholder with coordinates: " + str(absposx) + ", " + str( absposy) + " and width: " + str(width) +  " height: " + str(height) )
    background_img = pygame.image.load(background_img_path)
    background_img = pygame.transform.scale(background_img, (width, height))
    surface.blit(background_img, (absposx, absposy))
    refresh()
    return background_img

def check_keypress_end():
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q or event.key == pygame.K_a:
                logger.debug("Keypress 'a' or 'q' detected.")
                return True
            else:
                return False

def refresh():
    pygame.display.flip()


def destroy():
    pygame.quit()

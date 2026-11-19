(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable purple)
		(clear purple)
		(ontable blue)
		(on red blue)
		(clear red)

		(ontable orange)
		(on yellow orange)
		(on green yellow)
		(clear green)
	)
	(:goal (and (handempty robot)
		(ontable orange)
		(clear orange)
		(ontable blue)
		(on green blue)
		(clear green)

		(ontable purple)
		(on red purple)
		(on yellow red)
		(clear yellow)
	))
)
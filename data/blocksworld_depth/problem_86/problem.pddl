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
		(ontable yellow)
		(clear yellow)
		(ontable orange)
		(on purple orange)
		(clear purple)

		(ontable green)
		(on red green)
		(on blue red)
		(clear blue)
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